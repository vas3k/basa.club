import { rememberGeo } from "../lib/geo";

// Remembers chosen country/city and navigates to the option's data-url, keeping the search query
export default function geoSelect(form: HTMLElement) {
    const queryInput = form.querySelector<HTMLInputElement>("[name=query]");
    const countrySelect = form.querySelector<HTMLSelectElement>("[data-geo=country]");
    const citySelect = form.querySelector<HTMLSelectElement>("[data-geo=city]");

    form.querySelectorAll<HTMLSelectElement>("select[data-geo]").forEach((select) => {
        select.addEventListener("change", () => {
            const option = select.selectedOptions[0];
            if (!option) return;

            rememberGeo(
                countrySelect?.value || "everywhere",
                select.dataset.geo === "country" ? "everywhere" : citySelect?.value || "everywhere",
            );

            let url = option.dataset.url || "/";
            const query = queryInput?.value.trim();
            if (query) {
                url += `${url.includes("?") ? "&" : "?"}query=${encodeURIComponent(query)}`;
            }
            window.location.href = url;
        });
    });
}
