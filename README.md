# sm-ext-curl

A cURL extension in Sourcemod

A free and easy-to-use client-side URL transfer library, supporting DICT, FILE, FTP, FTPS, GOPHER, HTTP, HTTPS, IMAP, IMAPS, LDAP, LDAPS, POP3, POP3S, RTMP, RTSP, SCP, SFTP, SMTP, SMTPS, TELNET and TFTP. libcurl supports SSL certificates, HTTP POST, HTTP PUT, FTP uploading, HTTP form based upload, proxies, cookies, user+password authentication (Basic, Digest, NTLM, Negotiate, Kerberos), file transfer resume, http proxy tunneling and more!

http://curl.haxx.se/

http://www.sourcemod.net/

http://forums.alliedmods.net/showthread.php?t=152216

## Builds

CI builds Linux and Windows, x86 and x86_64, against SourceMod master, 1.12-dev and
1.13.0.7427. Each package holds `addons/sourcemod/extensions/curl.ext.so` (or `.dll`)
for x86 and `addons/sourcemod/extensions/x64/curl.ext.so` for x86_64. Pushing a tag
publishes them as a GitHub release.

The extension statically links the libraries `ci/build_deps.py` builds from pinned,
checksummed sources:

| Library | Version |
| --- | --- |
| libcurl | 8.23.0 |
| OpenSSL | 3.5.9 (LTS) |
| libssh2 | 1.11.1 |
| zlib | 1.3.2 |

Protocols built in: DICT, FILE, FTP(S), GOPHER(S), HTTP(S), IMAP(S), MQTT(S), POP3(S), RTSP,
SCP, SFTP, SMTP(S), TELNET, TFTP, WS(S); features: IPv6, threaded DNS, zlib, NTLM, SSL.
Not built in: LDAP, RTMP, HTTP/2, IDN, Kerberos/GSS-API.

Default CA store: `/etc/ssl/certs/ca-certificates.crt` on Linux, the Windows
certificate store on Windows (`CURLOPT_CAINFO` still overrides it).

To build locally, build the libraries once per arch, then run AMBuild with
[sm-ext-common](https://github.com/srcdslab/sm-ext-common):

```sh
python3 ci/build_deps.py --arch x86 --prefix deps/deps-linux-x86
python3 ci/build_deps.py --arch x86_64 --prefix deps/deps-linux-x86_64
mkdir build && cd build
python3 ../sm-ext-common/configure.py --sdks=css --sm-path=... --mms-path=... \
  --hl2sdk-root=... --hl2sdk-manifests-path=... --enable-optimize --ext-root ../
ambuild
```

## Changelog

v1.4.0 * Build for x86 and x86_64 (Linux and Windows) with the shared srcdslab AMBuild CI * Update libcurl to 8.23.0, OpenSSL to 3.5.9, libssh2 to 1.11.1, zlib to 1.3.2 (built from source in CI instead of bundled 32-bit binaries) * Keep the SHA-0 hash (Openssl_Hash_SHA) with a built-in implementation, OpenSSL dropped it * Fix 64-bit issues (long curl options passed as int, form lengths cast to pointers) and Windows FILE access
v1.3.0.0 (released) * Update libcurl to 7.23.1 * Update libssh2 to 1.3.0 * Add CURLOPT_* from new libcurl version * Add SendRecv_Act_GOTO_SEND_NO_WAIT & SendRecv_Act_GOTO_RECV_NO_WAIT
v1.2.0.0 (released) * Add curl_easy_setopt_function * Add CURLOPT_WRITEFUNCTION, CURLOPT_READFUNCTION support * Update smtp example * Add a example for CURLOPT_WRITEFUNCTION
v1.1.0.0 (released) * All handles no more automately close, should close it manually * Add curl_set_send_timeout, curl_set_recv_timeout * Add udp support * Add a udp example * Update self test & examples
v1.0.0.0 (released) * Initial Release
