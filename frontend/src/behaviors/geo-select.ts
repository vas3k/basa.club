export default function geoSelect(form: HTMLElement) {
    const countrySelect = form.querySelector<HTMLSelectElement>("[data-geo=country]");
    const citySelect = form.querySelector<HTMLSelectElement>("[data-geo=city]");

    form.querySelectorAll<HTMLSelectElement>("select[data-geo]").forEach((select) => {
        select.addEventListener("change", (event) => {
            const country = countrySelect?.value || "everywhere";
            const city = select.dataset.geo === "country" ? "everywhere" : citySelect?.value || "everywhere";
            event.stopPropagation();
            const target = new URL(placePath(country, city), window.location.origin);
            const query = form.querySelector<HTMLInputElement>('[name="query"]')?.value.trim().slice(0, 200);
            if (query) target.searchParams.set("query", query);
            window.location.assign(target.pathname + target.search);
        });
    });
}

function placePath(country: string, city: string) {
    if (country === "everywhere") return "/";
    if (city === "everywhere") return `/${encodeURIComponent(country)}/`;
    return `/${encodeURIComponent(country)}/${encodeURIComponent(city)}/`;
}
