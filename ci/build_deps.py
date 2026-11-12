#!/usr/bin/env python3
# Builds the static third-party libraries the extension links against
# (zlib, OpenSSL, libssh2, libcurl) for one target architecture, from pinned
# and checksummed source tarballs.
#
#   python3 ci/build_deps.py --arch x86|x86_64 --prefix <install dir> [--work <dir>]
#
# Linux: gcc (-m32 for x86, needs gcc-multilib), cmake, make, perl.
# Windows: run from a Visual Studio developer prompt for the target arch
# (ilammy/msvc-dev-cmd), with cmake, nmake and Strawberry Perl.
#
# The prefix ends up with include/ and lib/ holding libcurl, libssh2, libssl,
# libcrypto and zlib under fixed names (see LIB_NAMES), which src/AMBuilder
# links in that order.

import argparse
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request

# Pinned sources. Update the version, URL and SHA-256 together; the SHA-256 is
# the one GitHub publishes for the release asset (curl, OpenSSL, zlib) or the
# hash of the tarball whose GPG signature was checked (libssh2).
DEPS = {
    'zlib': (
        '1.3.2',
        'https://github.com/madler/zlib/releases/download/v1.3.2/zlib-1.3.2.tar.xz',
        'd7a0654783a4da529d1bb793b7ad9c3318020af77667bcae35f95d0e42a792f3',
    ),
    # 3.5 is the current OpenSSL LTS branch (supported until 2030-04-08).
    'openssl': (
        '3.5.9',
        'https://github.com/openssl/openssl/releases/download/openssl-3.5.9/openssl-3.5.9.tar.gz',
        '603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a',
    ),
    'libssh2': (
        '1.11.1',
        'https://github.com/libssh2/libssh2/releases/download/libssh2-1.11.1/libssh2-1.11.1.tar.xz',
        '9954cb54c4f548198a7cbebad248bdc87dd64bd26185708a294b2b50771e3769',
    ),
    'curl': (
        '8.23.0',
        'https://github.com/curl/curl/releases/download/curl-8_23_0/curl-8.23.0.tar.xz',
        '8dadd7d2536a314f982ad05a651b713f426bf7d02cc2c76cffb9796f2218e6c5',
    ),
}

WINDOWS = sys.platform == 'win32'

# Final library names in <prefix>/lib, in link order.
if WINDOWS:
    LIB_NAMES = ['libcurl.lib', 'libssh2.lib', 'libssl.lib', 'libcrypto.lib', 'zlib.lib']
else:
    LIB_NAMES = ['libcurl.a', 'libssh2.a', 'libssl.a', 'libcrypto.a', 'libz.a']


def log(msg):
    print('==> ' + msg, flush=True)


def run(cmd, cwd=None, env=None):
    log(' '.join(cmd) + ('  (in {})'.format(cwd) if cwd else ''))
    subprocess.check_call(cmd, cwd=cwd, env=env)


def jobs():
    return str(os.cpu_count() or 2)


def fetch(name, work):
    version, url, sha256 = DEPS[name]
    dl_dir = os.path.join(work, 'dl')
    os.makedirs(dl_dir, exist_ok=True)
    archive = os.path.join(dl_dir, url.rsplit('/', 1)[1])
    if not os.path.exists(archive):
        log('download ' + url)
        tmp = archive + '.part'
        with urllib.request.urlopen(url) as resp, open(tmp, 'wb') as out:
            shutil.copyfileobj(resp, out)
        os.replace(tmp, archive)

    digest = hashlib.sha256()
    with open(archive, 'rb') as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b''):
            digest.update(chunk)
    if digest.hexdigest() != sha256:
        os.remove(archive)
        raise SystemExit('SHA-256 mismatch for {}: got {}, expected {}'.format(
            archive, digest.hexdigest(), sha256))
    log('{} {} sha256 OK'.format(name, version))

    src_root = os.path.join(work, 'src')
    os.makedirs(src_root, exist_ok=True)
    src = os.path.join(src_root, '{}-{}'.format(name, version))
    if os.path.isdir(src):
        shutil.rmtree(src)
    with tarfile.open(archive) as tar:
        if hasattr(tarfile, 'data_filter'):
            tar.extractall(src_root, filter='data')
        else:
            tar.extractall(src_root)
    if not os.path.isdir(src):
        raise SystemExit('{} did not extract to {}'.format(archive, src))
    return src


def cmake_build(src, build, prefix, args, arch):
    if os.path.isdir(build):
        shutil.rmtree(build)
    cmd = ['cmake', '-S', src, '-B', build,
           '-DCMAKE_BUILD_TYPE=Release',
           '-DCMAKE_INSTALL_PREFIX=' + prefix,
           '-DCMAKE_INSTALL_LIBDIR=lib',
           '-DCMAKE_PREFIX_PATH=' + prefix,
           '-DBUILD_SHARED_LIBS=OFF',
           '-DBUILD_STATIC_LIBS=ON',
           '-DBUILD_TESTING=OFF']
    if WINDOWS:
        # NMake uses the compiler of the developer prompt, so the prompt's arch wins.
        # /MT matches the extension (sm-ext-common builds it with /MT).
        cmd += ['-G', 'NMake Makefiles',
                '-DCMAKE_POLICY_DEFAULT_CMP0091=NEW',
                '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded']
    else:
        flags = '-m32' if arch == 'x86' else '-m64'
        cmd += ['-DCMAKE_POSITION_INDEPENDENT_CODE=ON',
                '-DCMAKE_C_FLAGS=' + flags,
                '-DCMAKE_EXE_LINKER_FLAGS=' + flags,
                '-DCMAKE_SHARED_LINKER_FLAGS=' + flags]
    run(cmd + args)
    run(['cmake', '--build', build, '--parallel', jobs()])
    run(['cmake', '--install', build])


def find_lib(prefix, patterns):
    for pattern in patterns:
        hits = sorted(glob.glob(os.path.join(prefix, 'lib', pattern)))
        if hits:
            return hits[0]
    raise SystemExit('none of {} found in {}/lib'.format(patterns, prefix))


def rename_lib(prefix, patterns, final):
    found = find_lib(prefix, patterns)
    dest = os.path.join(prefix, 'lib', final)
    if os.path.normcase(found) != os.path.normcase(dest):
        shutil.copyfile(found, dest)
    return dest


def build_zlib(work, prefix, arch):
    src = fetch('zlib', work)
    cmake_build(src, os.path.join(work, 'build-zlib'), prefix, [
        '-DZLIB_BUILD_SHARED=OFF',
        '-DZLIB_BUILD_STATIC=ON',
        '-DZLIB_BUILD_TESTING=OFF',
    ], arch)
    if WINDOWS:
        return rename_lib(prefix, ['zs.lib', 'zlibstatic.lib', 'zlib.lib'], 'zlib.lib')
    return rename_lib(prefix, ['libz.a'], 'libz.a')


def build_openssl(work, prefix, arch):
    src = fetch('openssl', work)
    # md2 stays available because curl_hash_* exposes it (Openssl_Hash_MD2).
    common = ['no-shared', 'no-tests', 'no-docs', 'enable-md2',
              '--prefix=' + prefix, '--libdir=lib']
    if WINDOWS:
        target = 'VC-WIN32' if arch == 'x86' else 'VC-WIN64A'
        perl = r'C:\Strawberry\perl\bin\perl.exe'
        if not os.path.exists(perl):
            perl = 'perl'
        env = dict(os.environ)
        if perl != 'perl':
            # The Makefile calls perl again: Strawberry Perl must come first, not Git's msys perl.
            env['PATH'] = os.path.dirname(perl) + os.pathsep + env['PATH']
        # no-asm: no NASM on the runners; static build uses /MT /Zl.
        run([perl, 'Configure', target, 'no-asm',
             '--openssldir=' + os.path.join(prefix, 'ssl')] + common, cwd=src, env=env)
        run(['nmake', 'build_libs'], cwd=src, env=env)
        run(['nmake', 'install_dev'], cwd=src, env=env)
    else:
        target = 'linux-x86' if arch == 'x86' else 'linux-x86_64'
        # Same default OPENSSLDIR as the old bundled 0.9.8 build; the CA bundle is
        # set in curl instead (CURL_CA_BUNDLE).
        run(['perl', './Configure', target, '-fPIC',
             '--openssldir=/usr/local/ssl'] + common, cwd=src)
        run(['make', '-j' + jobs(), 'build_libs'], cwd=src)
        run(['make', 'install_dev'], cwd=src)
    ext = '.lib' if WINDOWS else '.a'
    return (rename_lib(prefix, ['libssl' + ext], 'libssl' + ext),
            rename_lib(prefix, ['libcrypto' + ext], 'libcrypto' + ext))


def openssl_args(prefix, ssl_lib, crypto_lib):
    return ['-DOPENSSL_ROOT_DIR=' + prefix,
            '-DOPENSSL_INCLUDE_DIR=' + os.path.join(prefix, 'include'),
            '-DOPENSSL_SSL_LIBRARY=' + ssl_lib,
            '-DOPENSSL_CRYPTO_LIBRARY=' + crypto_lib,
            '-DOPENSSL_USE_STATIC_LIBS=ON',
            '-DOPENSSL_MSVC_STATIC_RT=ON']


def build_libssh2(work, prefix, arch, ssl_lib, crypto_lib):
    src = fetch('libssh2', work)
    cmake_build(src, os.path.join(work, 'build-libssh2'), prefix, [
        '-DCRYPTO_BACKEND=OpenSSL',
        '-DBUILD_EXAMPLES=OFF',
        '-DENABLE_ZLIB_COMPRESSION=OFF',
    ] + openssl_args(prefix, ssl_lib, crypto_lib), arch)
    if WINDOWS:
        return rename_lib(prefix, ['libssh2_static.lib', 'libssh2.lib'], 'libssh2.lib')
    return rename_lib(prefix, ['libssh2.a'], 'libssh2.a')


def build_curl(work, prefix, arch, ssl_lib, crypto_lib, ssh2_lib, zlib_lib):
    src = fetch('curl', work)
    args = [
        '-DBUILD_CURL_EXE=OFF',
        '-DBUILD_EXAMPLES=OFF',
        '-DBUILD_LIBCURL_DOCS=OFF',
        '-DBUILD_MISC_DOCS=OFF',
        '-DENABLE_CURL_MANUAL=OFF',
        # Only the dependencies built here: never pick up a host library.
        '-DCURL_USE_PKGCONFIG=OFF',
        '-DCURL_USE_CMAKECONFIG=OFF',
        '-DCURL_USE_OPENSSL=ON',
        '-DCURL_USE_LIBSSH2=ON',
        '-DLIBSSH2_INCLUDE_DIR=' + os.path.join(prefix, 'include'),
        '-DLIBSSH2_LIBRARY=' + ssh2_lib,
        '-DCURL_ZLIB=ON',
        '-DZLIB_INCLUDE_DIR=' + os.path.join(prefix, 'include'),
        '-DZLIB_LIBRARY=' + zlib_lib,
        '-DCURL_BROTLI=OFF',
        '-DCURL_ZSTD=OFF',
        '-DUSE_NGHTTP2=OFF',
        '-DUSE_LIBIDN2=OFF',
        '-DCURL_USE_LIBPSL=OFF',
        '-DCURL_USE_GSSAPI=OFF',
        '-DCURL_DISABLE_LDAP=ON',
        # curl 8 makes NTLM opt-in; 7.23.1 had it and CURLAUTH_NTLM is part of the include.
        '-DCURL_ENABLE_NTLM=ON',
        '-DENABLE_ARES=OFF',
    ] + openssl_args(prefix, ssl_lib, crypto_lib)
    if WINDOWS:
        # Verify peers against the Windows certificate store by default.
        args += ['-DCURL_STATIC_CRT=ON', '-DCURL_CA_NATIVE=ON',
                 '-DCURL_CA_BUNDLE=none', '-DCURL_CA_PATH=none']
    else:
        # Same default bundle as the old bundled 7.23.1 build (Debian/Ubuntu path).
        args += ['-DCURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt',
                 '-DCURL_CA_PATH=/etc/ssl/certs']
    cmake_build(src, os.path.join(work, 'build-curl'), prefix, args, arch)
    if WINDOWS:
        return rename_lib(prefix, ['libcurl.lib', 'libcurl_a.lib', 'libcurl-d.lib'], 'libcurl.lib')
    return rename_lib(prefix, ['libcurl.a'], 'libcurl.a')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', required=True, choices=['x86', 'x86_64'])
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--work', default=None)
    opts = parser.parse_args()

    prefix = os.path.abspath(opts.prefix)
    work = os.path.abspath(opts.work or os.path.join(prefix + '-work'))
    os.makedirs(prefix, exist_ok=True)
    os.makedirs(work, exist_ok=True)

    zlib_lib = build_zlib(work, prefix, opts.arch)
    ssl_lib, crypto_lib = build_openssl(work, prefix, opts.arch)
    ssh2_lib = build_libssh2(work, prefix, opts.arch, ssl_lib, crypto_lib)
    build_curl(work, prefix, opts.arch, ssl_lib, crypto_lib, ssh2_lib, zlib_lib)

    for name in LIB_NAMES:
        path = os.path.join(prefix, 'lib', name)
        if not os.path.isfile(path):
            raise SystemExit('missing ' + path)
    with open(os.path.join(prefix, 'VERSIONS.txt'), 'w') as fp:
        for name, (version, url, sha256) in DEPS.items():
            fp.write('{} {} {}\n'.format(name, version, sha256))
    log('done: ' + prefix)


if __name__ == '__main__':
    main()
