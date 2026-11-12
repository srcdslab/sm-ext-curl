#ifndef _INCLUDE_SOURCEMOD_EXTENSION_SHA0_H_
#define _INCLUDE_SOURCEMOD_EXTENSION_SHA0_H_

#include <stddef.h>
#include <stdint.h>

/**
 * SHA-0 (FIPS 180, 1993), kept for Openssl_Hash_SHA: OpenSSL dropped SHA()
 * and SHA_Init() in 1.1.0. Do not use it for anything new.
 */

#define SHA0_DIGEST_LENGTH	20

struct SHA0_CTX {
	uint32_t h[5];
	uint64_t length;
	unsigned char block[64];
	size_t used;
};

void SHA0_Init(SHA0_CTX *c);
void SHA0_Update(SHA0_CTX *c, const void *data, size_t len);
void SHA0_Final(unsigned char *md, SHA0_CTX *c);
void SHA0(const unsigned char *data, size_t len, unsigned char *md);

#endif
