set -eu
R=/root/deagle-svcomp26-repro-20261021-01a15ee7
cd "$R"
mkdir -p runtime/packages runtime/rootfs
tar -xf archives/runtime-bundle.tar -C runtime/packages
tar -xzf runtime/packages/ubuntu-base-24.04.3-base-amd64.tar.gz -C runtime/rootfs
for p in runtime/packages/*.deb; do dpkg-deb -x "$p" runtime/rootfs; done
mkdir -p runtime/rootfs/tool runtime/rootfs/benchmarks runtime/rootfs/runs runtime/rootfs/dev runtime/rootfs/proc
cp -a sources/official-tool/deagle/. runtime/rootfs/tool/
cp -a sources/sv-benchmarks/c runtime/rootfs/benchmarks/
test -e runtime/rootfs/dev/null || mknod -m 666 runtime/rootfs/dev/null c 1 3
test -e runtime/rootfs/dev/zero || mknod -m 666 runtime/rootfs/dev/zero c 1 5
test -e runtime/rootfs/dev/urandom || mknod -m 666 runtime/rootfs/dev/urandom c 1 9
test -e runtime/rootfs/dev/random || mknod -m 666 runtime/rootfs/dev/random c 1 8
chroot runtime/rootfs /bin/sh -c 'python3 --version; gcc --version; ldd --version; /tool/deagle --version; /tool/deagle_exe --version' > evidence/runtime-versions.txt 2>&1
cat evidence/runtime-versions.txt
sha256sum runtime/rootfs/tool/deagle runtime/rootfs/tool/deagle_exe > evidence/official-runtime-tool-sha256.txt
