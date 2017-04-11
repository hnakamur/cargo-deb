#!/bin/sh
set -e
echo ""
echo "This needs a local copy of cargo-vendor, and the following packages:"
echo "python-dulwich python-pytoml devscripts"
echo ""

TMPDIR=`mktemp -d`
echo "Using '${TMPDIR}'..."
cat > "${TMPDIR}/Makefile" <<'EOF'
include /usr/share/dpkg/pkg-info.mk
all:
	@echo $(DEB_VERSION_UPSTREAM)
EOF
WORKDIR=${PWD}

if [ -z "$1" ]
  then
    USCAN_ARGS="";
    CARGO_VER=$(make -f "${TMPDIR}/Makefile");
  else
    USCAN_ARGS="--download-version $1";
    CARGO_VER="$1";
fi;

BOOTSTRAP_PY=$(find "${PWD}" -name bootstrap.py -type f)
DEPS_FILTER=$(find "${PWD}" -name deps-tarball-filter.txt -type f)

# Download cargo tarball
uscan --rename ${USCAN_ARGS} --force-download --destdir "${TMPDIR}/"

# Extract cargo source
cd "${TMPDIR}"
mkdir cargo
tar -xaf "${TMPDIR}/cargo_${CARGO_VER}.orig.tar.gz" -C cargo --strip-components=1
cd cargo

# Trim the list of dependencies
echo ""
echo "Applying clean-cargo-deps.patch... If this fails, remember to refresh the patch first!"
patch -p1 < ${WORKDIR}/debian/patches/clean-cargo-deps.patch

# Download build-deps via cargo-vendor
export GIT_AUTHOR_NAME="deb-build"
export GIT_AUTHOR_EMAIL="<>"
export GIT_COMMITTER_NAME="${GIT_AUTHOR_NAME}"
export GIT_COMMITTER_EMAIL="${GIT_AUTHOR_EMAIL}"
cargo vendor --explicit-version --verbose deps

# Unpack artifacts and clean embedded libs
${WORKDIR}/debian/cargo-vendor-unpack.py
grep -v '^#' ${DEPS_FILTER} | xargs  -I% sh -c 'rm -rf deps/%' &&
tar -czf "${TMPDIR}/cargo_${CARGO_VER}.orig-deps.tar.gz" deps

# All is good, we are done!
echo "Your files are available at:"
echo "${TMPDIR}/cargo_${CARGO_VER}.orig.tar.gz \\"
echo "${TMPDIR}/cargo_${CARGO_VER}.orig-deps.tar.gz"
echo ""
echo "Unpacked cargo sources are availabe under:"
echo "${TMPDIR}/cargo/"
