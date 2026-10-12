export default function formChange(form: HTMLElement) {
    if (!(form instanceof HTMLFormElement)) return;

    form.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLSelectElement)
            && !(target instanceof HTMLInputElement && ["checkbox", "radio"].includes(target.type))) return;

        const option = target instanceof HTMLSelectElement ? target.selectedOptions[0] : undefined;
        const base = option?.dataset.url || form.getAttribute("action") || window.location.pathname;
        const url = new URL(base, window.location.origin);
        if (form.method === "post") {
            form.action = url.pathname + url.search + url.hash;
            form.requestSubmit();
            return;
        }

        const params = new URLSearchParams();
        for (const [name, value] of new FormData(form)) {
            if (typeof value !== "string" || value === "") continue;
            params.set(name, value);
        }

        const query = params.toString();
        window.location.href = url.pathname + (query ? `?${query}` : "") + url.hash;
    });
}
