#!/bin/bash
# build_mesa.sh: Mesa 25.0.7 panfrost (Mali-T720, GLES2) for the Android 15 vendor, cross-built on the Mac
# with NDK r27 and installed (stripped) into android/work/vendor. Mesa >= 25.1 needs LLVM/libclc on
# the host for panfrost's libpan CL kernels, so stay on 25.0.x.
# Sources in gpu/src (mesa-25.0.7, libdrm-2.4.134); host python deps in gpu/venv (mako, pyyaml, meson).
set -e
G=$(cd "$(dirname "$0")" && pwd); V=$G/../android/work/vendor
NDK=~/Library/Android/sdk/ndk/27.2.12479018/toolchains/llvm/prebuilt/darwin-x86_64/bin
export PATH=$G/venv/bin:/opt/homebrew/opt/bison/bin:$PATH

if [ ! -f $G/prefix/lib/libdrm.a ]; then
  (cd $G/src/libdrm-2.4.134 && meson setup $G/build-libdrm --cross-file $G/android-aarch64.cross \
    --prefix=$G/prefix --libdir=lib --default-library=static -Dintel=disabled -Dradeon=disabled \
    -Damdgpu=disabled -Dnouveau=disabled -Dvmwgfx=disabled -Domap=disabled -Dexynos=disabled \
    -Dfreedreno=disabled -Dtegra=disabled -Dvc4=disabled -Detnaviv=disabled -Dcairo-tests=disabled \
    -Dvalgrind=disabled -Dman-pages=disabled -Dtests=false -Dinstall-test-programs=false -Dudev=false)
  ninja -C $G/build-libdrm install
fi

if [ ! -f $G/build-mesa/build.ninja ]; then
  (cd $G/src/mesa-25.0.7 && meson setup $G/build-mesa --cross-file $G/android-aarch64.cross \
    --prefix=/vendor --libdir=lib64 --buildtype=release -Db_ndebug=true \
    -Dplatforms=android -Dplatform-sdk-version=35 -Dandroid-stub=true -Dandroid-libbacktrace=disabled \
    -Dandroid-strict=false -Dgallium-drivers=panfrost -Dvulkan-drivers= -Dllvm=disabled -Degl=enabled \
    -Dgles1=enabled -Dgles2=enabled -Dopengl=false -Dglx=disabled -Dgbm=disabled \
    -Degl-lib-suffix=_mesa -Dgles-lib-suffix=_mesa -Dexpat=disabled -Dzstd=disabled -Dxmlconfig=disabled \
    -Dvalgrind=disabled -Dlibunwind=disabled -Dlmsensors=disabled -Dbuild-tests=false -Dtools= \
    -Dvideo-codecs= -Dgallium-va=disabled -Dgallium-vdpau=disabled -Dgallium-xa=disabled)
fi
ninja -C $G/build-mesa

B=$G/build-mesa; S=$NDK/llvm-strip; mkdir -p $V/lib64/egl
$S -o $V/lib64/egl/libEGL_mesa.so       $B/src/egl/libEGL_mesa.so
$S -o $V/lib64/egl/libGLESv2_mesa.so    $B/src/mapi/es2api/libGLESv2_mesa.so
$S -o $V/lib64/egl/libGLESv1_CM_mesa.so $B/src/mapi/es1api/libGLESv1_CM_mesa.so
$S -o $V/lib64/libgallium_dri.so        $B/src/gallium/targets/dri/libgallium_dri.so
# libhardware.so + libz.so in vendor/lib64 are copies of the GSI's /system/lib64 ones (not reachable
# from the sphal namespace); Mesa's android_stub libhardware must NOT be shipped (hw_get_module returns 0).
ls -la $V/lib64/egl $V/lib64/libgallium_dri.so
