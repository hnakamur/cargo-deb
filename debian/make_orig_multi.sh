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
VENDOR_FILTER=$(find "${PWD}" -name vendor-tarball-filter.txt -type f)
VENDOR_SUS_WHITELIST=$(find "${PWD}" -name vendor-tarball-unsuspicious.txt -type f)

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
cargo vendor --explicit-version --verbose

# Clean embedded libs and update checksums
grep -v '^#' ${VENDOR_FILTER} | xargs  -I% sh -c 'rm -rf vendor/%'
for i in vendor/*; do ${WORKDIR}/debian/scripts/prune-checksums "$i"; done

# Report any suspicious files
cp -R vendor vendor-scan
grep -v '^#' ${VENDOR_SUS_WHITELIST} | xargs  -I% sh -c 'rm -rf vendor-scan/%'
echo "Checking for suspicious files..."
# The following shell snippet is a bit more strict than suspicious-source(1)
find vendor-scan -type f -and -not -name '.cargo-checksum.json' -exec file '{}' \; | \
  sed -e 's/\btext\b\(.*\), with very long lines/verylongtext\1/g' | \
  grep -v '\b\(text\|empty\)\b' || true
echo "The above files (if any) seem suspicious, please audit them."
echo "If good, add them to ${VENDOR_SUS_WHITELIST}."
echo "If bad, add them to ${VENDOR_FILTER}."
rm -rf vendor-scan

# Pack it up, reproducibly
GZIP=-9n tar --sort=name \
    --mtime="./Cargo.lock" \
    --owner=root --group=root \
    -czf "${TMPDIR}/cargo_${CARGO_VER}.orig-vendor.tar.gz" vendor

# All is good, we are done!
echo "Your files are available at:"
echo "${TMPDIR}/cargo_${CARGO_VER}.orig.tar.gz \\"
echo "${TMPDIR}/cargo_${CARGO_VER}.orig-vendor.tar.gz"
echo ""
echo "Unpacked cargo sources are available under:"
echo "${TMPDIR}/cargo/"
