#!/bin/sh
set -e
echo "This needs python-dulwich python-pytoml installed"

TMPDIR=`mktemp -d`
echo "Using '${TMPDIR}'..."
cat > "${TMPDIR}/Makefile" <<'EOF'
include /usr/share/dpkg/pkg-info.mk
all:
	@echo $(DEB_VERSION_UPSTREAM)
EOF
CARGO_VER=$(make -f "${TMPDIR}/Makefile")
BOOTSTRAP_PY=$(find "${PWD}" -name bootstrap.py -type f)
DEPS_FILTER=$(find "${PWD}" -name deps-tarball-filter.txt -type f)

# Download cargo tarballs
uscan --rename --force-download --destdir ${TMPDIR}

# Download crates.io-index snapshotted for this cargo 
. debian/crates.io-index
echo "${DOWNLOAD_URL}"
wget -O "${TMPDIR}/cargo_${CARGO_VER}.orig-index.tar.gz" "${DOWNLOAD_URL}"

# Extract cargo source
cd "${TMPDIR}"
mkdir cargo
tar -xaf "${TMPDIR}/cargo_${CARGO_VER}.orig.tar.gz" -C cargo --strip-components=1
cd cargo

# Extract crates.io-index snapshot
mkdir index
tar -xaf "${TMPDIR}/cargo_${CARGO_VER}.orig-index.tar.gz" -C index --strip-components=1

# Download build-dep packages from crates.io
# (target spec is dummy/unused here)
mkdir deps
${BOOTSTRAP_PY} --download \
                --no-clean \
                --no-clone \
                --crate-index "${TMPDIR}/cargo/index/" \
                --cargo-root "${TMPDIR}/cargo" \
                --target-dir "${TMPDIR}/cargo/deps/" \
                --target x86_64-unknown-linux-gnu
cd deps && grep -v '^#' ${DEPS_FILTER} | xargs  -I% sh -c "rm -rf %" && cd ..
tar -czf "${TMPDIR}/cargo_${CARGO_VER}.orig-deps.tar.gz" deps

# All is good, we are done!
echo "Your files are available at:"
echo "${TMPDIR}/cargo_${CARGO_VER}.orig.tar.gz \\"
echo "${TMPDIR}/cargo_${CARGO_VER}.orig-index.tar.gz \\"
echo "${TMPDIR}/cargo_${CARGO_VER}.orig-deps.tar.gz"
echo ""
echo "Unpacked cargo sources are availabe under:"
echo "${TMPDIR}/cargo/"
