export function setCookie(name: string, value: string, maxAgeSeconds: number) {
    document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; samesite=lax`;
}
