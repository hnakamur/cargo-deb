#!/usr/bin/env python
"""
About
=====

This python script is design to do the bare minimum to compile and link the
Cargo binary for the purposes of bootstrapping itself on a new platform for
which cross-compiling isn't possible.  I wrote this specifically to bootstrap
Cargo on [Bitrig](https://bitrig.org).  Bitrig is a fork of OpenBSD that uses
clang/clang++ and other BSD licensed tools instead of GNU licensed software.
Cross compiling from another platform is extremely difficult because of the
alternative toolchain Bitrig uses.

With this script, all that should be necessary to run this is a working Rust
toolchain, Python, and Git.

This script will not set up a full cargo cache or anything.  It works by
cloning the cargo index and then starting with the cargo dependencies, it
recursively builds the dependency tree.  Once it has the dependency tree, it
starts with the leaves of the tree, doing a breadth first traversal and for
each dependency, it clones the repo, sets the repo's head to the correct
revision and then executes the build command specified in the cargo config.

This bootstrap script uses a temporary directory to store the built dependency
libraries and uses that as a link path when linking dependencies and the
cargo binary.  The goal is to create a statically linked cargo binary that is
capable of being used as a "local cargo" when running the main cargo Makefiles.

Dependencies
============

* pytoml -- used for parsing toml files.
  https://github.com/avakar/pytoml

* dulwich -- used for working with git repos.
  https://git.samba.org/?p=jelmer/dulwich.git;a=summary

Both can be installed via the pip tool:

```sh
sudo pip install pytoml dulwich
```

Command Line Options
====================

```
--cargo-root <path>    specify the path to the cargo repo root.
--target-dir <path>    specify the location to store build results.
--crate-index <path>   path to where crates.io index shoudl be cloned
--no-clone             don't clone crates.io index, --crate-index must point to existing clone.
--no-clean             don't remove the folders created during bootstrapping.
--download             only download the crates needed to bootstrap cargo.
--graph                output dot format graph of dependencies.
--target <triple>      build target: e.g. x86_64-unknown-bitrig
--host <triple>        host machine: e.g. x86_64-unknown-linux-gnu
--test-semver          triggers the execution of the Semver and SemverRange class tests.
```

The `--cargo-root` option defaults to the current directory if unspecified.  The
target directory defaults to Python equivilent of `mktemp -d` if unspecified.
The `--crate-index` option specifies where the crates.io index will be cloned.  Or,
if you already have a clone of the index, the crates index should point there
and you should also specify `--no-clone`.  The `--target` option is used to
specify which platform you are bootstrapping for.  The `--host` option defaults
to the value of the `--target` option when not specified.

Examples
========

To bootstrap Cargo on (Bitrig)[https://bitrig.org] I followed these steps:

* Cloned this [bootstrap script repo](https://github.com/dhuseby/cargo-bootstra)
to `/tmp/bootstrap`.
* Cloned the [crates.io index](https://github.com/rust-lang/crates.io-index)
to `/tmp/index`.
* Created a target folder, `/tmp/out`, for the output.
* Cloned the (Cargo)[https://github.com/rust-lang/cargo] repo to `/tmp/cargo`.
* Copied the bootstrap.py script to the cargo repo root.
* Ran the bootstrap.py script like so:
```sh
./bootstrap.py --crate-index /tmp/index --target-dir /tmp/out --no-clone --no-clean --target x86_64-unknown-bitrig
```

After the script completed, there is a Cargo executable named `cargo-0_2_0` in
`/tmp/out`.  That executable can then be used to bootstrap Cargo from source by
specifying it as the `--local-cargo` option to Cargo's `./configure` script.
"""

import argparse, \
       cStringIO, \
       hashlib, \
       httplib, \
       inspect, \
       json, \
       os, \
       re, \
       shutil, \
       subprocess, \
       sys, \
       tarfile, \
       tempfile, \
       urlparse
import pytoml as toml
import dulwich.porcelain as git

TARGET = None
HOST = None
GRAPH = None
CRATES_INDEX = 'git://github.com/rust-lang/crates.io-index.git'
CARGO_REPO = 'git://github.com/rust-lang/cargo.git'
CRATE_API_DL = 'https://crates.io/api/v1/crates/%s/%s/download'
SV_RANGE = re.compile('^(?P<op>(?:\<=|\>=|=|\<|\>|\^|\~))?\s*'
                      '(?P<major>(?:\*|0|[1-9][0-9]*))'
                      '(\.(?P<minor>(?:\*|0|[1-9][0-9]*)))?'
                      '(\.(?P<patch>(?:\*|0|[1-9][0-9]*)))?'
                      '(\-(?P<prerelease>[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?'
                      '(\+(?P<build>[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$')
SEMVER = re.compile('^\s*(?P<major>(?:0|[1-9][0-9]*))'
                    '(\.(?P<minor>(?:0|[1-9][0-9]*)))?'
                    '(\.(?P<patch>(?:0|[1-9][0-9]*)))?'
                    '(\-(?P<prerelease>[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?'
                    '(\+(?P<build>[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$')
BSCRIPT = re.compile('^cargo:(?P<key>([^\s=]+))(=(?P<value>.+))?$')
BNAME = re.compile('^(lib)?(?P<name>([^_]+))(_.*)?$')
BUILT = {}
CRATES = {}
UNRESOLVED = []
PFX = []

def idnt(f):
    def do_indent(*cargs):
        ret = f(*cargs)
        return ret
    return do_indent

def dbgCtx(f):
    def do_dbg(self, *cargs):
        global PFX
        PFX.append(self.name())
        ret = f(self, *cargs)
        PFX.pop()
        return ret
    return do_dbg

def dbg(s):
    global PFX
    print '%s: %s' % (':'.join(PFX), s)

class PreRelease(object):

    def __init__(self, pr):
        self._container = []
        if pr is not None:
            self._container += str(pr).split('.')

    def __str__(self):
        return '.'.join(self._container)

    def __repr__(self):
        return self._container

    def __getitem__(self, key):
        return self._container[key]

    def __len__(self):
        return len(self._container)

    def __gt__(self, rhs):
        return not ((self < rhs) or (self == rhs))

    def __ge__(self, rhs):
        return not (self < rhs)

    def __le__(self, rhs):
        return not (self > rhs)

    def __eq__(self, rhs):
        return self._container == rhs._container

    def __ne__(self, rhs):
        return not (self == rhs)

    def __lt__(self, rhs):
        if self == rhs:
            return False

        # not having a pre-release is higher precedence
        if len(self) == 0:
            if len(rhs) == 0:
                return False
            else:
                # 1.0.0 > 1.0.0-alpha
                return False
        else:
            if len(rhs) is None:
                # 1.0.0-alpha < 1.0.0
                return True

        # if both have one, then longer pre-releases are higher precedence
        if len(self) > len(rhs):
            # 1.0.0-alpha.1 > 1.0.0-alpha
            return False
        elif len(self) < len(rhs):
            # 1.0.0-alpha < 1.0.0-alpha.1
            return True

        # if both have the same length pre-release, must check each piece
        # numeric sub-parts have lower precedence than non-numeric sub-parts
        # non-numeric sub-parts are compared lexically in ASCII sort order
        for l,r in zip(self, rhs):
            if l.isdigit():
                if r.isdigit():
                    if int(l) < int(r):
                        # 2 > 1
                        return True
                    elif int(l) > int(r):
                        # 1 < 2
                        return False
                    else:
                        # 1 == 1
                        continue
                else:
                    # 1 < 'foo'
                    return True
            else:
                if r.isdigit():
                    # 'foo' > 1
                    return False

            # both are non-numeric
            if l < r:
                return True
            elif l > r:
                return False

        raise RuntimeError('PreRelease __lt__ failed')


class Semver(dict):

    def __init__(self, sv):
        match = SEMVER.match(str(sv))
        if match is None:
            raise ValueError('%s is not a valid semver string' % sv)

        self._input = sv
        self.update(match.groupdict())
        self.prerelease = PreRelease(self['prerelease'])

    def __str__(self):
        major, minor, patch, prerelease, build = self.parts_raw()
        s = ''
        if major is None:
            s += '0'
        else:
            s += major
        s += '.'
        if minor is None:
            s += '0'
        else:
            s += minor
        s += '.'
        if patch is None:
            s += '0'
        else:
            s += patch
        if len(self.prerelease):
            s += '-' + str(self.prerelease)
        if build is not None:
            s += '+' + build
        return s

    def __hash__(self):
        return hash(str(self))

    def as_range(self):
        return SemverRange('=%s' % self)

    def parts(self):
        major, minor, patch, prerelease, build = self.parts_raw()
        if major is None:
            major = '0'
        if minor is None:
            minor = '0'
        if patch is None:
            patch = '0'
        return (int(major),int(minor),int(patch),prerelease,build)

    def parts_raw(self):
        return (self['major'],self['minor'],self['patch'],self['prerelease'],self['build'])

    def __lt__(self, rhs):
        lmaj,lmin,lpat,lpre,_ = self.parts()
        rmaj,rmin,rpat,rpre,_ = rhs.parts()
        if lmaj < rmaj:
            return True
        elif lmin < rmin:
            return True
        elif lpat < rpat:
            return True
        elif lpre is not None and rpre is None:
            return True
        elif lpre is not None and rpre is not None:
            if self.prerelease < rhs.prerelease:
                return True
        return False

    def __le__(self, rhs):
        return not (self > rhs)

    def __gt__(self, rhs):
        return not ((self < rhs) or (self == rhs))

    def __ge__(self, rhs):
        return not (self < rhs)

    def __eq__(self, rhs):
        # build metadata is only considered for equality
        lmaj,lmin,lpat,lpre,lbld = self.parts()
        rmaj,rmin,rpat,rpre,rbld = rhs.parts()
        return lmaj == rmaj and \
               lmin == rmin and \
               lpat == rpat and \
               lpre == rpre and \
               lbld == rbld

    def __ne__(self, rhs):
        return not (self == rhs)


class SemverRange(dict):

    def __init__(self, sv):
        match = SV_RANGE.match(str(sv))
        if match is None:
            raise ValueError('%s is not a valid semver range string' % sv)

        self._input = sv
        self.update(match.groupdict())
        self.prerelease = PreRelease(self['prerelease'])

        # fix up the op
        op = self['op']
        if op is None:
            if self['major'] == '*' or self['minor'] == '*' or self['patch'] == '*':
                op = '*'
            else:
                # if no op was specified and there are no wildcards, then op
                # defaults to '^'
                op = '^'
        else:
            self._semver = Semver(sv[len(op):])

        if op not in ('<=', '>=', '<', '>', '=', '^', '~', '*'):
            raise ValueError('%s is not a valid semver operator' % op)

        self['op'] = op

    def parts_raw(self):
        return (self['major'],self['minor'],self['patch'],self['prerelease'],self['build'])

    def __str__(self):
        major, minor, patch, prerelease, build = self.parts_raw()
        if self['op'] == '*':
            if self['major'] == '*':
                return '*'
            elif self['minor'] == '*':
                return major + '*'
            else:
                return major + '.' + minor + '.*'
        else:
            s = self['op']
            if major is None:
                s += '0'
            else:
                s += major
            s += '.'
            if minor is None:
                s += '0'
            else:
                s += minor
            s += '.'
            if patch is None:
                s += '0'
            else:
                s += patch
            if len(self.prerelease):
                s += '-' + str(self.prerelease)
            if build is not None:
                s += '+' + build
            return s

    def lower(self):
        op = self['op']
        major,minor,patch,_,_ = self.parts_raw()

        if op in ('<=', '<', '=', '>', '>='):
            return None

        if op == '*':
            # wildcards specify a range
            if self['major'] == '*':
                return Semver('0.0.0')
            elif self['minor'] == '*':
                return Semver(major + '.0.0')
            elif self['patch'] == '*':
                return Semver(major + '.' + minor + '.0')
        elif op == '^':
            # caret specifies a range
            if patch is None:
                if minor is None:
                    # ^0 means >=0.0.0 and <1.0.0
                    return Semver(major + '.0.0')
                else:
                    # ^0.0 means >=0.0.0 and <0.1.0
                    return Semver(major + '.' + minor + '.0')
            else:
                # ^0.0.1 means >=0.0.1 and <0.0.2
                # ^0.1.2 means >=0.1.2 and <0.2.0
                # ^1.2.3 means >=1.2.3 and <2.0.0
                if int(major) == 0:
                    if int(minor) == 0:
                        # ^0.0.1
                        return Semver('0.0.' + patch)
                    else:
                        # ^0.1.2
                        return Semver('0.' + minor + '.' + patch)
                else:
                    # ^1.2.3
                    return Semver(major + '.' + minor + '.' + patch)
        elif op == '~':
            # tilde specifies a minimal range
            if patch is None:
                if minor is None:
                    # ~0 means >=0.0.0 and <1.0.0
                    return Semver(major + '.0.0')
                else:
                    # ~0.0 means >=0.0.0 and <0.1.0
                    return Semver(major + '.' + minor + '.0')
            else:
                # ~0.0.1 means >=0.0.1 and <0.1.0
                # ~0.1.2 means >=0.1.2 and <0.2.0
                # ~1.2.3 means >=1.2.3 and <1.3.0
                return Semver(major + '.' + minor + '.' + patch)

        raise RuntimeError('No lower bound')

    def upper(self):
        op = self['op']
        major,minor,patch,_,_ = self.parts_raw()

        if op in ('<=', '<', '=', '>', '>='):
            return None

        if op == '*':
            # wildcards specify a range
            if self['major'] == '*':
                return None
            elif self['minor'] == '*':
                return Semver(str(int(major) + 1) + '.0.0')
            elif self['patch'] == '*':
                return Semver(major + '.' + str(int(minor) + 1) + '.0')
        elif op == '^':
            # caret specifies a range
            if patch is None:
                if minor is None:
                    # ^0 means >=0.0.0 and <1.0.0
                    return Semver(str(int(major) + 1) + '.0.0')
                else:
                    # ^0.0 means >=0.0.0 and <0.1.0
                    return Semver(major + '.' + str(int(minor) + 1) + '.0')
            else:
                # ^0.0.1 means >=0.0.1 and <0.0.2
                # ^0.1.2 means >=0.1.2 and <0.2.0
                # ^1.2.3 means >=1.2.3 and <2.0.0
                if int(major) == 0:
                    if int(minor) == 0:
                        # ^0.0.1
                        return Semver('0.0.' + str(int(patch) + 1))
                    else:
                        # ^0.1.2
                        return Semver('0.' + str(int(minor) + 1) + '.0')
                else:
                    # ^1.2.3
                    return Semver(str(int(major) + 1) + '.0.0')
        elif op == '~':
            # tilde specifies a minimal range
            if patch is None:
                if minor is None:
                    # ~0 means >=0.0.0 and <1.0.0
                    return Semver(str(int(major) + 1) + '.0.0')
                else:
                    # ~0.0 means >=0.0.0 and <0.1.0
                    return Semver(major + '.' + str(int(minor) + 1) + '.0')
            else:
                # ~0.0.1 means >=0.0.1 and <0.1.0
                # ~0.1.2 means >=0.1.2 and <0.2.0
                # ~1.2.3 means >=1.2.3 and <1.3.0
                return Semver(major + '.' + str(int(minor) + 1) + '.0')

        raise RuntimeError('No upper bound')

    def compare(self, sv):
        if type(sv) is not Semver:
            sv = Semver(sv)

        op = self['op']
        major,minor,patch,_,_ = self.parts_raw()

        if op == '*':
            if self['major'] == '*':
                return sv >= Semver('0.0.0')

            return (sv >= self.lower()) and (sv < self.upper())
        elif op == '^':
            return (sv >= self.lower()) and (sv < self.upper())
        elif op == '~':
            return (sv >= self.lower()) and (sv < self.upper())
        elif op == '<=':
            return sv <= self._semver
        elif op == '>=':
            return sv >= self._semver
        elif op == '<':
            return sv < self._semver
        elif op == '>':
            return sv > self._semver
        elif op == '=':
            return sv == self._semver

        raise RuntimeError('Semver comparison failed to find a matching op')

def test_semver():
    print '\ntesting parsing:'
    print '"1"                    is: "%s"' % Semver("1")
    print '"1.1"                  is: "%s"' % Semver("1.1")
    print '"1.1.1"                is: "%s"' % Semver("1.1.1")
    print '"1.1.1-alpha"          is: "%s"' % Semver("1.1.1-alpha")
    print '"1.1.1-alpha.1"        is: "%s"' % Semver("1.1.1-alpha.1")
    print '"1.1.1-alpha+beta"     is: "%s"' % Semver("1.1.1-alpha+beta")
    print '"1.1.1-alpha.1+beta"   is: "%s"' % Semver("1.1.1-alpha.1+beta")
    print '"1.1.1-alpha.1+beta.1" is: "%s"' % Semver("1.1.1-alpha.1+beta.1")

    print '\ntesting equality:'
    print '"1"                    == "1.0.0"                is: %s' % (Semver("1") == Semver("1.0.0"))
    print '"1.1"                  == "1.1.0"                is: %s' % (Semver("1.1") == Semver("1.1.0"))
    print '"1.1.1"                == "1.1.1"                is: %s' % (Semver("1.1.1") == Semver("1.1.1"))
    print '"1.1.1-alpha"          == "1.1.1-alpha"          is: %s' % (Semver("1.1.1-alpha") == Semver("1.1.1-alpha"))
    print '"1.1.1-alpha.1"        == "1.1.1-alpha.1"        is: %s' % (Semver("1.1.1-alpha.1") == Semver("1.1.1-alpha.1"))
    print '"1.1.1-alpha+beta"     == "1.1.1-alpha+beta"     is: %s' % (Semver("1.1.1-alpha+beta") == Semver("1.1.1-alpha+beta"))
    print '"1.1.1-alpha.1+beta"   == "1.1.1-alpha.1+beta"   is: %s' % (Semver("1.1.1-alpha.1+beta") == Semver("1.1.1-alpha.1+beta"))
    print '"1.1.1-alpha.1+beta.1" == "1.1.1-alpha.1+beta.1" is: %s' % (Semver("1.1.1-alpha.1+beta.1") == Semver("1.1.1-alpha.1+beta.1"))

    print '\ntesting less than:'
    print '"1"                  < "2.0.0"              is: %s' % (Semver("1") < Semver("2.0.0"))
    print '"1.1"                < "1.2.0"              is: %s' % (Semver("1.1") < Semver("1.2.0"))
    print '"1.1.1"              < "1.1.2"              is: %s' % (Semver("1.1.1") < Semver("1.1.2"))
    print '"1.1.1-alpha"        < "1.1.1"              is: %s' % (Semver("1.1.1-alpha") < Semver("1.1.1"))
    print '"1.1.1-alpha"        < "1.1.1-beta"         is: %s' % (Semver("1.1.1-alpha") < Semver("1.1.1-beta"))
    print '"1.1.1-1"            < "1.1.1-alpha"        is: %s' % (Semver("1.1.1-alpha") < Semver("1.1.1-beta"))
    print '"1.1.1-alpha"        < "1.1.1-alpha.1"      is: %s' % (Semver("1.1.1-alpha") < Semver("1.1.1-alpha.1"))
    print '"1.1.1-alpha.1"      < "1.1.1-alpha.2"      is: %s' % (Semver("1.1.1-alpha.1") < Semver("1.1.1-alpha.2"))
    print '"1.1.1-alpha+beta"   < "1.1.1+beta"         is: %s' % (Semver("1.1.1-alpha+beta") < Semver("1.1.1+beta"))
    print '"1.1.1-alpha+beta"   < "1.1.1-beta+beta"    is: %s' % (Semver("1.1.1-alpha+beta") < Semver("1.1.1-beta+beta"))
    print '"1.1.1-1+beta"       < "1.1.1-alpha+beta"   is: %s' % (Semver("1.1.1-alpha+beta") < Semver("1.1.1-beta+beta"))
    print '"1.1.1-alpha+beta"   < "1.1.1-alpha.1+beta" is: %s' % (Semver("1.1.1-alpha+beta") < Semver("1.1.1-alpha.1+beta"))
    print '"1.1.1-alpha.1+beta" < "1.1.1-alpha.2+beta" is: %s' % (Semver("1.1.1-alpha.1+beta") < Semver("1.1.1-alpha.2+beta"))

    print '\ntesting semver range parsing:'
    print '"0"      lower: %s, upper: %s' % (SemverRange('0').lower(), SemverRange('0').upper())
    print '"0.0"    lower: %s, upper: %s' % (SemverRange('0.0').lower(), SemverRange('0.0').upper())
    print '"0.0.0"  lower: %s, upper: %s' % (SemverRange('0.0.0').lower(), SemverRange('0.0.0').upper())
    print '"0.0.1"  lower: %s, upper: %s' % (SemverRange('0.0.1').lower(), SemverRange('0.0.1').upper())
    print '"0.1.1"  lower: %s, upper: %s' % (SemverRange('0.1.1').lower(), SemverRange('0.1.1').upper())
    print '"1.1.1"  lower: %s, upper: %s' % (SemverRange('1.1.1').lower(), SemverRange('1.1.1').upper())
    print '"^0"     lower: %s, upper: %s' % (SemverRange('^0').lower(), SemverRange('^0').upper())
    print '"^0.0"   lower: %s, upper: %s' % (SemverRange('^0.0').lower(), SemverRange('^0.0').upper())
    print '"^0.0.0" lower: %s, upper: %s' % (SemverRange('^0.0.0').lower(), SemverRange('^0.0.0').upper())
    print '"^0.0.1" lower: %s, upper: %s' % (SemverRange('^0.0.1').lower(), SemverRange('^0.0.1').upper())
    print '"^0.1.1" lower: %s, upper: %s' % (SemverRange('^0.1.1').lower(), SemverRange('^0.1.1').upper())
    print '"^1.1.1" lower: %s, upper: %s' % (SemverRange('^1.1.1').lower(), SemverRange('^1.1.1').upper())
    print '"~0"     lower: %s, upper: %s' % (SemverRange('~0').lower(), SemverRange('~0').upper())
    print '"~0.0"   lower: %s, upper: %s' % (SemverRange('~0.0').lower(), SemverRange('~0.0').upper())
    print '"~0.0.0" lower: %s, upper: %s' % (SemverRange('~0.0.0').lower(), SemverRange('~0.0.0').upper())
    print '"~0.0.1" lower: %s, upper: %s' % (SemverRange('~0.0.1').lower(), SemverRange('~0.0.1').upper())
    print '"~0.1.1" lower: %s, upper: %s' % (SemverRange('~0.1.1').lower(), SemverRange('~0.1.1').upper())
    print '"~1.1.1" lower: %s, upper: %s' % (SemverRange('~1.1.1').lower(), SemverRange('~1.1.1').upper())
    print '"*"      lower: %s, upper: %s' % (SemverRange('*').lower(), SemverRange('*').upper())
    print '"0.*"    lower: %s, upper: %s' % (SemverRange('0.*').lower(), SemverRange('0.*').upper())
    print '"0.0.*"  lower: %s, upper: %s' % (SemverRange('0.0.*').lower(), SemverRange('0.0.*').upper())


class Runner(object):

    def __init__(self, c, e, cwd=None):
        self._cmd = c
        if type(self._cmd) is not list:
            self._cmd = [self._cmd]
        self._env = e
        self._stdout = []
        self._stderr = []
        self._returncode = 0
        self._cwd = cwd

    def __call__(self, c, e):
        cmd = self._cmd + c
        env = dict(self._env, **e)
        #dbg(' env: %s' % env)
        #dbg(' cwd: %s' % self._cwd)
        envstr = ''
        for k,v in env.iteritems():
            envstr += ' %s="%s"' % (k, v)
        if self._cwd is not None:
            dbg('cd %s && %s %s' % (self._cwd, envstr, ' '.join(cmd)))
        else:
            dbg('%s %s' % (envstr, ' '.join(cmd)))

        proc = subprocess.Popen(cmd, env=env, \
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                cwd=self._cwd)
        out, err = proc.communicate()

        for lo in out.split('\n'):
            if len(lo) > 0:
                self._stdout.append(lo)
                #dbg('out: %s' % lo)

        for le in err.split('\n'):
            if len(le) > 0:
                self._stderr.append(le)
                dbg(le)

        """
        while proc.poll() is None:
            lo = proc.stdout.readline().rstrip('\n')
            le = proc.stderr.readline().rstrip('\n')
            if len(lo) > 0:
                self._stdout.append(lo)
                dbg(lo)
                sys.stdout.flush()
            if len(le) > 0:
                self._stderr.append(le)
                dbg('err: %s', le)
                sys.stdout.flush()
        """
        self._returncode = proc.wait()
        #dbg(' ret: %s' % self._returncode)
        return self._stdout

    def output(self):
        return self._stdout

    def returncode(self):
        return self._returncode

class RustcRunner(Runner):

    def __call__(self, c, e):
        super(RustcRunner, self).__call__(c, e)
        return ([], {}, {})

class BuildScriptRunner(Runner):

    def __call__(self, c, e):
        #dbg('XXX Running build script:');
        #dbg(' env: %s' % e)
        #dbg(' '.join(self._cmd + c))
        super(BuildScriptRunner, self).__call__(c, e)

        # parse the output for cargo: lines
        cmd = []
        env = {}
        denv = {}
        for l in self.output():
            match = BSCRIPT.match(str(l))
            if match is None:
                continue
            pieces = match.groupdict()
            k = pieces['key']
            v = pieces['value']

            if k == 'rustc-link-lib':
                #dbg('YYYYYY: adding -l %s' % v)
                cmd += ['-l', v]
            elif k == 'rustc-link-search':
                #dbg("adding link search path: %s" % v)
                cmd += ['-L', v]
            elif k == 'rustc-cfg':
                cmd += ['--cfg', v]
                env['CARGO_FEATURE_%s' % v.upper().replace('-','_')] = 1
            else:
                #dbg("env[%s] = %s" % (k, v));
                denv[k] = v
        return (cmd, env, denv)

class Crate(object):

    def __init__(self, crate, ver, deps, cdir, build):
        self._crate = str(crate)
        self._version = Semver(ver)
        self._dep_info = deps
        self._dir = cdir
        # put the build scripts first
        self._build = filter(lambda x: x.get('type', None) == 'build_script', build)
        # then add the lib/bin builds
        self._build += filter(lambda x: x.get('type', None) != 'build_script', build)
        self._resolved = False
        self._deps = {}
        self._refs = []
        self._env = {}
        self._dep_env = {}
        self._extra_flags = []

    def name(self):
        return self._crate

    def dep_info(self):
        return self._dep_info

    def version(self):
        return self._version

    def dir(self):
        return self._dir

    def __str__(self):
        return '%s-%s' % (self.name(), self.version())

    def add_dep(self, crate, features):
        if self._deps.has_key(str(crate)):
            return

        features = [str(x) for x in features]
        self._deps[str(crate)] = { 'features': features }
        crate.add_ref(self)

    def add_ref(self, crate):
        if str(crate) not in self._refs:
            self._refs.append(str(crate))

    def resolved(self):
        return self._resolved

    @dbgCtx
    def resolve(self, tdir, idir, graph=None):
        global CRATES
        global UNRESOLVED

        if self._resolved:
            return
        if CRATES.has_key(str(self)):
            return

        if self._dep_info is not None:
            print ''
            dbg('Resolving dependencies for: %s' % str(self))
            for d in self._dep_info:
                kind = d.get('kind', 'normal')
                if kind not in ('normal', 'build'):
                    print ''
                    dbg('Skipping %s dep %s' % (kind, d['name']))
                    continue

                optional = d.get('optional', False)
                if optional:
                    print ''
                    dbg('Skipping optional dep %s' % d['name'])
                    continue

                svr = SemverRange(d['req'])
                print ''
                deps = []
                dbg('Looking up info for %s %s' % (d['name'], str(svr)))
                if d.get('local', None) is None:
                    # go through crates first to see if the is satisfied already
                    dcrate = find_crate_by_name_and_semver(d['name'], svr)
                    if dcrate is not None:
                        #import pdb; pdb.set_trace()
                        svr = dcrate.version().as_range()
                    name, ver, ideps, ftrs, cksum = crate_info_from_index(idir, d['name'], svr)
                    if dcrate is None:
                        cdir = dl_and_check_crate(tdir, name, ver, cksum)
                        _, tver, tdeps, build = crate_info_from_toml(cdir)
                        deps += ideps
                        deps += tdeps
                    else:
                        dbg('Found crate already satisfying %s %s' % (d['name'], str(svr)))
                        deps += dcrate.dep_info()
                else:
                    cdir = d['path']
                    name, ver, ideps, build = crate_info_from_toml(cdir)
                    deps += ideps

                try:
                    if dcrate is None:
                        dcrate = Crate(name, ver, deps, cdir, build)
                        if CRATES.has_key(str(dcrate)):
                            dcrate = CRATES[str(dcrate)]
                    UNRESOLVED.append(dcrate)
                    if graph is not None:
                        print >> graph, '"%s" -> "%s";' % (str(self), str(dcrate))

                except:
                    dcrate = None

                # clean up the list of features that are enabled
                tftrs = d.get('features', [])
                if type(tftrs) is dict:
                    tftrs = tftrs.keys()
                else:
                    tftrs = filter(lambda x: len(x) > 0, tftrs)

                # add 'default' if default_features is true
                if d.get('default_features', True):
                    tftrs.append('default')

                features = []
                if type(ftrs) is dict:
                    # add any available features that are activated by the
                    # dependency entry in the parent's dependency record,
                    # and any features they depend on recursively
                    def add_features(f):
                        if ftrs.has_key(f):
                            for k in ftrs[f]:
                                # guard against infinite recursion
                                if not k in features:
                                    features.append(k)
                                    add_features(k)
                    for k in tftrs:
                        add_features(k)
                else:
                    features += filter(lambda x: (len(x) > 0) and (x in tftrs), ftrs)

                if dcrate is not None:
                    self.add_dep(dcrate, features)

        self._resolved = True
        CRATES[str(self)] = self

    @dbgCtx
    def build(self, by, out_dir, features=[]):
        global BUILT
        global CRATES
        global TARGET
        global HOST

        extra_filename = '-' + str(self.version()).replace('.','_')
        output_name = self.name().replace('-','_')
        output = os.path.join(out_dir, 'lib%s%s.rlib' % (output_name, extra_filename))

        if BUILT.has_key(str(self)):
            return ({'name':self.name(), 'lib':output}, self._env, self._extra_flags)

        externs = []
        extra_flags = []
        for dep,info in self._deps.iteritems():
            if CRATES.has_key(dep):
                extern, env, extra_flags = CRATES[dep].build(self, out_dir, info['features'])
                externs.append(extern)
                self._dep_env[CRATES[dep].name()] = env
                self._extra_flags += extra_flags

        if os.path.isfile(output):
            print ''
            dbg('Skipping %s, already built (needed by: %s)' % (str(self), str(by)))
            BUILT[str(self)] = str(by)
            return ({'name':self.name(), 'lib':output}, self._env, self._extra_flags)

        # build the environment for subcommands
        tenv = dict(os.environ)
        env = {}
        env['PATH'] = tenv['PATH']
        env['OUT_DIR'] = out_dir
        env['TARGET'] = TARGET
        env['HOST'] = HOST
        env['NUM_JOBS'] = '1'
        env['OPT_LEVEL'] = '0'
        env['DEBUG'] = '0'
        env['PROFILE'] = 'release'
        env['CARGO_MANIFEST_DIR'] = self.dir()
        env['CARGO_PKG_VERSION_MAJOR'] = self.version()['major']
        env['CARGO_PKG_VERSION_MINOR'] = self.version()['minor']
        env['CARGO_PKG_VERSION_PATCH'] = self.version()['patch']
        pre = self.version()['prerelease']
        if pre is None:
            pre = ''
        env['CARGO_PKG_VERSION_PRE'] = pre
        env['CARGO_PKG_VERSION'] = str(self.version())
        for f in features:
            env['CARGO_FEATURE_%s' % f.upper().replace('-','_')] = '1'
        for l,e in self._dep_env.iteritems():
            for k,v in e.iteritems():
                if type(v) is not str and type(v) is not unicode:
                    v = str(v)
                env['DEP_%s_%s' % (l.upper(), v.upper())] = v

        # create the builders, build scrips are first
        cmds = []
        for b in self._build:
            v = str(self._version).replace('.','_')
            cmd = ['rustc']
            cmd.append(os.path.join(self._dir, b['path']))
            cmd.append('--crate-name')
            if b['type'] == 'lib':
                cmd.append(b['name'].replace('-','_'))
                cmd.append('--crate-type')
                cmd.append('lib')
            elif b['type'] == 'build_script':
                cmd.append('build_script_%s' % b['name'].replace('-','_'))
                cmd.append('--crate-type')
                cmd.append('bin')
            else:
                cmd.append(b['name'].replace('-','_'))
                cmd.append('--crate-type')
                cmd.append('bin')

            for f in features:
                cmd.append('--cfg')
                cmd.append('feature=\"%s\"' % f)

            cmd.append('-C')
            cmd.append('extra-filename=' + extra_filename)

            cmd.append('--out-dir')
            cmd.append('%s' % out_dir)
            cmd.append('--emit=dep-info,link')
            cmd.append('--target')
            cmd.append(TARGET)
            cmd.append('-L')
            cmd.append('%s' % out_dir)
            cmd.append('-L')
            cmd.append('%s/lib' % out_dir)


            # add in the flags from dependencies
            cmd += self._extra_flags

            for e in externs:
                cmd.append('--extern')
                cmd.append('%s=%s' % (e['name'].replace('-','_'), e['lib']))

            # get the pkg key name
            match = BNAME.match(b['name'])
            if match is not None:
                match = match.groupdict()['name'].replace('-','_')

            # queue up the runner
            cmds.append({'name':b['name'], 'env_key':match, 'cmd':RustcRunner(cmd, env)})

            # queue up the build script runner
            if b['type'] == 'build_script':
                bcmd = os.path.join(out_dir, 'build_script_%s-%s' % (b['name'], v))
                cmds.append({'name':b['name'], 'env_key':match, 'cmd':BuildScriptRunner(bcmd, env, self._dir)})

        print ''
        dbg('Building %s (needed by: %s)' % (str(self), str(by)))

        bcmd = []
        benv = {}
        for c in cmds:
            runner = c['cmd']

            (c1, e1, e2) = runner(bcmd, benv)

            if runner.returncode() != 0:
                raise RuntimeError('build command failed: %s' % runner.returncode())

            bcmd += c1
            benv = dict(benv, **e1)

            key = c['env_key']
            for k,v in e2.iteritems():
                self._env['DEP_%s_%s' % (key.upper(), k.upper())] = v

            #dbg('XXX  cmd: %s' % bcmd)
            #dbg('XXX  env: %s' % benv)
            #dbg('XXX denv: %s' % self._env)
            #print ''

        BUILT[str(self)] = str(by)
        return ({'name':self.name(), 'lib':output}, self._env, bcmd)

@idnt
def dl_crate(url, depth=0):
    if depth > 10:
        raise RuntimeError('too many redirects')

    loc = urlparse.urlparse(url)
    if loc.scheme == 'https':
        conn = httplib.HTTPSConnection(loc.netloc)
    elif loc.scheme == 'http':
        conn = httplib.HTTPConnection(loc.netloc)
    else:
        raise RuntimeError('unsupported url scheme: %s' % loc.scheme)

    conn.request("GET", loc.path)
    res = conn.getresponse()
    dbg('%sconnected to %s...%s' % ((' ' * depth), url, res.status))
    headers = dict(res.getheaders())
    if headers.has_key('location') and headers['location'] != url:
        return dl_crate(headers['location'], depth + 1)

    return res.read()

@idnt
def dl_and_check_crate(tdir, name, ver, cksum):
    global CRATES
    cname = '%s-%s' % (name, ver)
    cdir = os.path.join(tdir, cname)
    if CRATES.has_key(cname):
        dbg('skipping %s...already downloaded' % cname)
        return cdir

    if not os.path.isdir(cdir):
        dbg('Downloading %s source to %s' % (cname, cdir))
        dl = CRATE_API_DL % (name, ver)
        buf = dl_crate(dl)
        if (cksum is not None):
            h = hashlib.sha256()
            h.update(buf)
            if h.hexdigest() == cksum:
                dbg('Checksum is good...%s' % cksum)
            else:
                dbg('Checksum is BAD (%s != %s)' % (h.hexdigest(), cksum))

        fbuf = cStringIO.StringIO(buf)
        with tarfile.open(fileobj=fbuf) as tf:
            dbg('unpacking result to %s...' % cdir)
            tf.extractall(path=tdir)

    return cdir

@idnt
def crate_info_from_toml(cdir):
    try:
        with open(os.path.join(cdir, 'Cargo.toml'), 'rb') as ctoml:
            #import pdb; pdb.set_trace()
            cfg = toml.load(ctoml)
            build = []
            p = cfg.get('package',cfg.get('project', {}))
            name = p.get('name', None)
            #if name == 'num_cpus':
            #    import pdb; pdb.set_trace()
            ver = p.get('version', None)
            if (name is None) or (ver is None):
                import pdb; pdb.set_trace()
                raise RuntimeError('invalid .toml file format')

            # look for a "links" item
            lnks = p.get('links', [])
            if type(lnks) is not list:
                lnks = [lnks]

            # look for a "build" item
            bf = p.get('build', None)

            # if we have a 'links', there must be a 'build'
            if len(lnks) > 0 and bf is None:
                import pdb; pdb.set_trace()
                raise RuntimeError('cargo requires a "build" item if "links" is specified')

            # there can be target specific build script overrides
            boverrides = {}
            for lnk in lnks:
                boverrides.update(cfg.get('target', {}).get(TARGET, {}).get(lnk, {}))

            bmain = False
            if bf is not None:
                build.append({'type':'build_script', \
                              'path':[ bf ], \
                              'name':name.replace('-','_'), \
                              'links': lnks, \
                              'overrides': boverrides})

            # look for libs array
            libs = cfg.get('lib', [])
            if type(libs) is not list:
                libs = [libs]
            for l in libs:
                l['type'] = 'lib'
                l['links'] = lnks
                if l.get('path', None) is None:
                    l['path'] = [ 'lib.rs' ]
                build.append(l)
                bmain = True

            # look for bins array
            bins = cfg.get('bin', [])
            if type(bins) is not list:
                bins = [bins]
            for b in bins:
                if b.get('path', None) is None:
                    b['path'] = [ os.path.join('bin', '%s.rs' % b['name']), os.path.join('bin', 'main.rs'), '%s.rs' % b['name'], 'main.rs' ]
                build.append({'type': 'bin', \
                              'name':b['name'], \
                              'path':b['path'], \
                              'links': lnks})
                bmain = True

            # if no explicit directions on what to build, then add a default
            if bmain == False:
                build.append({'type':'lib', 'path':'lib.rs', 'name':name.replace('-','_')})

            for b in build:
                # make sure the path is a list of possible paths
                if type(b['path']) is not list:
                    b['path'] = [ b['path'] ]
                bin_paths = []
                for p in b['path']:
                    bin_paths.append(os.path.join(cdir, p))
                    bin_paths.append(os.path.join(cdir, 'src', p))

                found_path = None
                for p in bin_paths:
                    if os.path.isfile(p):
                        found_path = p
                        break

                if found_path == None:
                    import pdb; pdb.set_trace()
                    raise RuntimeError('could not find %s to build in %s', (build, cdir))
                else:
                    b['path'] = found_path

            d = cfg.get('build-dependencies', {})
            d.update(cfg.get('dependencies', {}))
            d.update(cfg.get('target', {}).get(TARGET, {}).get('dependencies', {}))
            deps = []
            for k,v in d.iteritems():
                if type(v) is not dict:
                    deps.append({'name':k, 'req': v})
                elif v.has_key('path'):
                    if v.get('version', None) is None:
                        deps.append({'name':k, 'path':os.path.join(cdir, v['path']), 'local':True, 'req':0})
                    else:
                        opts = v.get('optional',False)
                        ftrs = v.get('features',[])
                        deps.append({'name':k, 'path': v['path'], 'req':v['version'], 'features':ftrs, 'optional':opts})
                else:
                    opts = v.get('optional',False)
                    ftrs = v.get('features',[])
                    deps.append({'name':k, 'req':v['version'], 'features':ftrs, 'optional':opts})

            return (name, ver, deps, build)

    except Exception, e:
        import pdb; pdb.set_trace()
        dbg('failed to load toml file for: %s (%s)' % (cdir, str(e)))

    return (None, None, [], 'lib.rs')

@idnt
def crate_info_from_index(idir, name, svr):
    global TARGET

    if len(name) == 1:
        ipath = os.path.join(idir, '1', name)
    elif len(name) == 2:
        ipath = os.path.join(idir, '2', name)
    elif len(name) == 3:
        ipath = os.path.join(idir, '3', name[0:1], name)
    else:
        ipath = os.path.join(idir, name[0:2], name[2:4], name)

    dbg('opening crate info: %s' % ipath)
    dep_infos = []
    with open(ipath, 'rb') as fin:
        lines = fin.readlines()
        for l in lines:
            dep_infos.append(json.loads(l))

    passed = {}
    for info in dep_infos:
        if not info.has_key('vers'):
            continue
        sv = Semver(info['vers'])
        if svr.compare(sv):
            passed[sv] = info

    keys = sorted(passed.iterkeys())
    best_match = keys.pop()
    dbg('best match is %s-%s' % (name, best_match))
    best_info = passed[best_match]
    name = best_info.get('name', None)
    ver = best_info.get('vers', None)
    deps = best_info.get('deps', [])
    ftrs = best_info.get('features', [])
    cksum = best_info.get('cksum', None)

    # only include deps without a 'target' or ones with matching 'target'
    deps = filter(lambda x: x.get('target', TARGET) == TARGET, deps)

    return (name, ver, deps, ftrs, cksum)

def find_crate_by_name_and_semver(name, svr):
    global CRATES
    global UNRESOLVED
    for c in CRATES.itervalues():
        if c.name() == name and svr.compare(c.version()):
            return c
    for c in UNRESOLVED:
        if c.name() == name and svr.compare(c.version()):
            return c
    return None

def args_parser():
    parser = argparse.ArgumentParser(description='Cargo Bootstrap Tool')
    parser.add_argument('--cargo-root', type=str,  default=os.getcwd(),
                        help="specify the cargo repo root path")
    parser.add_argument('--target-dir', type=str, default=tempfile.mkdtemp(),
                        help="specify the path for storing built dependency libs")
    parser.add_argument('--crate-index', type=str, default=None,
                        help="path to where the crate index should be cloned")
    parser.add_argument('--target', type=str, default=None,
                        help="target triple for machine we're bootstrapping for")
    parser.add_argument('--host', type=str, default=None,
                        help="host triple for machine we're bootstrapping on")
    parser.add_argument('--test-semver', action='store_true',
                        help="run semver parsing tests")
    parser.add_argument('--no-clone', action='store_true',
                        help="skip cloning crates index, --target-dir must point to an existing clone of the crates index")
    parser.add_argument('--no-git', action='store_true',
                        help="don't assume that the crates index and cargo root are git repos; implies --no-clone")
    parser.add_argument('--no-clean', action='store_true',
                        help="don't delete the target dir and crate index")
    parser.add_argument('--download', action='store_true',
                        help="only download the crates needed to build cargo")
    parser.add_argument('--graph', action='store_true',
                        help="output a dot graph of the dependencies")
    return parser

@idnt
def open_or_clone_repo(rdir, rurl, no_clone):
    try:
        repo = git.open_repo(rdir)
        return repo
    except:
        repo = None

    if repo is None and no_clone is False:
        dbg('Cloning %s to %s' % (rurl, rdir))
        return git.clone(rurl, rdir)

    return repo

if __name__ == "__main__":
    try:
        # parse args
        parser = args_parser()
        args = parser.parse_args()

        if args.test_semver:
            test_semver()
            sys.exit(0)

        # clone the cargo index
        if args.crate_index is None:
            args.crate_index = os.path.normpath(os.path.join(args.target_dir, 'index'))
        dbg('cargo: %s, target: %s, index: %s' % \
              (args.cargo_root, args.target_dir, args.crate_index))

        TARGET = args.target
        HOST = args.host

        if not args.no_git:
            index = open_or_clone_repo(args.crate_index, CRATES_INDEX, args.no_clone)
            cargo = open_or_clone_repo(args.cargo_root, CARGO_REPO, args.no_clone)

            if index is None:
                raise RuntimeError('You must have a local clone of the crates index, ' \
                                   'omit --no-clone to allow this script to clone it for ' \
                                   'you, or pass --no-git to bypass this check.')
            if cargo is None:
                raise RuntimeError('You must have a local clone of the cargo repo ' \
                                   'so that this script can read the cargo toml file.')

        if TARGET is None:
            raise RuntimeError('You must specify the target triple of this machine')
        if HOST is None:
            HOST = TARGET

    except Exception, e:
        frame = inspect.trace()[-1]
        print >> sys.stderr, "\nException:\n from %s, line %d:\n %s\n" % (frame[1], frame[2], e)
        parser.print_help()
        if not args.no_clean:
            shutil.rmtree(args.target_dir)
        sys.exit(1)

    try:

        # load cargo deps
        name, ver, deps, build = crate_info_from_toml(args.cargo_root)
        cargo_crate = Crate(name, ver, deps, args.cargo_root, build)
        UNRESOLVED.append(cargo_crate)

        if args.graph:
            GRAPH = open(os.path.join(args.target_dir, 'deps.dot'), 'wb')
            print >> GRAPH, "digraph %s {" % name

        # resolve and download all of the dependencies
        print ''
        print '===================================='
        print '===== DOWNLOADING DEPENDENCIES ====='
        print '===================================='
        while len(UNRESOLVED) > 0:
            crate = UNRESOLVED.pop(0)
            crate.resolve(args.target_dir, args.crate_index, GRAPH)

        if args.graph:
            print >> GRAPH, "}"
            GRAPH.close()

        if args.download:
            print "done downloading..."
            sys.exit(0)

        # build cargo
        print ''
        print '=========================='
        print '===== BUILDING CARGO ====='
        print '=========================='
        cargo_crate.build('bootstrap.py', args.target_dir)

        # cleanup
        if not args.no_clean:
            print "cleaning up..."
            shutil.rmtree(args.target_dir)
        print "done"

    except Exception, e:
        frame = inspect.trace()[-1]
        print >> sys.stderr, "\nException:\n from %s, line %d:\n %s\n" % (frame[1], frame[2], e)
        if not args.no_clean:
            shutil.rmtree(args.target_dir)
        sys.exit(1)


