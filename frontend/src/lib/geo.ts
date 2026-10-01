import { setCookie } from "./cookies";

const GEO_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

// Listings filter by these cookies (see geo/middleware.py), not by the geo in the URL
export function rememberGeo(country: string, city: string) {
    setCookie("country", country || "everywhere", GEO_COOKIE_MAX_AGE);
    setCookie("city", city || "everywhere", GEO_COOKIE_MAX_AGE);
}
