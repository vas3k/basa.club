import { rememberGeo } from "../lib/geo";

// Remembers country/city cookies when a geo select changes.
// Navigation is handled by form-change via each option's data-url.
export default function geoSelect(form: HTMLElement) {
    const countrySelect = form.querySelector<HTMLSelectElement>("[data-geo=country]");
    const citySelect = form.querySelector<HTMLSelectElement>("[data-geo=city]");

    form.querySelectorAll<HTMLSelectElement>("select[data-geo]").forEach((select) => {
        select.addEventListener("change", () => {
            rememberGeo(
                countrySelect?.value || "everywhere",
                select.dataset.geo === "country" ? "everywhere" : citySelect?.value || "everywhere",
            );
        });
    });
}
