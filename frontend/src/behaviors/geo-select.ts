import { setCookie } from "../lib/cookies";

const YEAR = 31536000;

export default function geoSelect(form: HTMLElement) {
    const countrySelect = form.querySelector<HTMLSelectElement>("[data-geo=country]");
    const citySelect = form.querySelector<HTMLSelectElement>("[data-geo=city]");

    form.querySelectorAll<HTMLSelectElement>("select[data-geo]").forEach((select) => {
        select.addEventListener("change", (event) => {
            const country = countrySelect?.value || "everywhere";
            const city = select.dataset.geo === "country" ? "everywhere" : citySelect?.value || "everywhere";
            setCookie("country", country, YEAR);
            setCookie("city", city, YEAR);
            event.stopPropagation();
            window.location.assign(placePath(country, city));
        });
    });
}

function placePath(country: string, city: string) {
    if (country === "everywhere") return "/";
    if (city === "everywhere") return `/${encodeURIComponent(country)}/`;
    return `/${encodeURIComponent(country)}/${encodeURIComponent(city)}/`;
}
