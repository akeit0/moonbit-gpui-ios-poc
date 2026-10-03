#pragma once
// The distributed env.c calls getentropy in chunks of at most 256 bytes.
// Supply that one missing Darwin interface through the iOS Security framework.
#include <Security/SecRandom.h>
#include <errno.h>
#include <stddef.h>

static inline int moon_mobile_getentropy(void *buffer, size_t length) {
    if (length > 256) { errno = EIO; return -1; }
    if (SecRandomCopyBytes(kSecRandomDefault, length, buffer) != errSecSuccess) {
        errno = EIO;
        return -1;
    }
    return 0;
}
#define getentropy moon_mobile_getentropy
