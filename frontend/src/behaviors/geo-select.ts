import { setCookie } from "../lib/cookies";

// Navigation is handled by form-change via each option's data-url.
export default function geoSelect(form: HTMLElement) {
    const countrySelect = form.querySelector<HTMLSelectElement>("[data-geo=country]");
    const citySelect = form.querySelector<HTMLSelectElement>("[data-geo=city]");

    form.querySelectorAll<HTMLSelectElement>("select[data-geo]").forEach((select) => {
        select.addEventListener("change", () => {
            const country = countrySelect?.value || "everywhere";
            const city = select.dataset.geo === "country" ? "everywhere" : citySelect?.value || "everywhere";
            setCookie("country", country, 31536000);
            setCookie("city", city, 31536000);
        });
    });
}
