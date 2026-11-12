#include "sha0.h"
#include <string.h>

#define ROL32(x, n)	(((x) << (n)) | ((x) >> (32 - (n))))

static void SHA0_Block(SHA0_CTX *c, const unsigned char *p)
{
	uint32_t w[80];
	for(int i = 0; i < 16; i++)
	{
		w[i] = ((uint32_t)p[i*4] << 24) | ((uint32_t)p[i*4+1] << 16) | ((uint32_t)p[i*4+2] << 8) | (uint32_t)p[i*4+3];
	}
	// SHA-0 differs from SHA-1 only here: no rotation in the message schedule.
	for(int i = 16; i < 80; i++)
	{
		w[i] = w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16];
	}

	uint32_t a = c->h[0], b = c->h[1], d = c->h[3], e = c->h[4];
	uint32_t cc = c->h[2];
	for(int i = 0; i < 80; i++)
	{
		uint32_t f, k;
		if(i < 20) {
			f = (b & cc) | (~b & d);
			k = 0x5A827999;
		} else if(i < 40) {
			f = b ^ cc ^ d;
			k = 0x6ED9EBA1;
		} else if(i < 60) {
			f = (b & cc) | (b & d) | (cc & d);
			k = 0x8F1BBCDC;
		} else {
			f = b ^ cc ^ d;
			k = 0xCA62C1D6;
		}
		uint32_t t = ROL32(a, 5) + f + e + k + w[i];
		e = d;
		d = cc;
		cc = ROL32(b, 30);
		b = a;
		a = t;
	}

	c->h[0] += a;
	c->h[1] += b;
	c->h[2] += cc;
	c->h[3] += d;
	c->h[4] += e;
}

void SHA0_Init(SHA0_CTX *c)
{
	c->h[0] = 0x67452301;
	c->h[1] = 0xEFCDAB89;
	c->h[2] = 0x98BADCFE;
	c->h[3] = 0x10325476;
	c->h[4] = 0xC3D2E1F0;
	c->length = 0;
	c->used = 0;
}

void SHA0_Update(SHA0_CTX *c, const void *data, size_t len)
{
	const unsigned char *p = (const unsigned char *)data;
	c->length += (uint64_t)len;
	while(len > 0)
	{
		size_t n = 64 - c->used;
		if(n > len)
			n = len;
		memcpy(&c->block[c->used], p, n);
		c->used += n;
		p += n;
		len -= n;
		if(c->used == 64)
		{
			SHA0_Block(c, c->block);
			c->used = 0;
		}
	}
}

void SHA0_Final(unsigned char *md, SHA0_CTX *c)
{
	uint64_t bits = c->length * 8;
	unsigned char pad = 0x80;
	SHA0_Update(c, &pad, 1);
	pad = 0;
	while(c->used != 56)
	{
		SHA0_Update(c, &pad, 1);
	}
	unsigned char len_be[8];
	for(int i = 0; i < 8; i++)
	{
		len_be[i] = (unsigned char)(bits >> (56 - i * 8));
	}
	SHA0_Update(c, len_be, 8);

	for(int i = 0; i < 5; i++)
	{
		md[i*4] = (unsigned char)(c->h[i] >> 24);
		md[i*4+1] = (unsigned char)(c->h[i] >> 16);
		md[i*4+2] = (unsigned char)(c->h[i] >> 8);
		md[i*4+3] = (unsigned char)c->h[i];
	}
}

void SHA0(const unsigned char *data, size_t len, unsigned char *md)
{
	SHA0_CTX c;
	SHA0_Init(&c);
	SHA0_Update(&c, data, len);
	SHA0_Final(md, &c);
}
