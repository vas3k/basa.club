// <form method="get" data-behavior="form-change"> submits when a select, checkbox or radio changes.
// GET updates the current path from named fields (empty values omitted). POST calls requestSubmit().
// If the changed <option> has data-url, that path is used instead of form.action.

const CHANGEABLE = new Set(["checkbox", "radio"]);

function shouldSubmit(target: EventTarget | null): boolean {
    if (target instanceof HTMLSelectElement) return true;
    return target instanceof HTMLInputElement && CHANGEABLE.has(target.type);
}

function destination(form: HTMLFormElement, target: EventTarget | null): URL {
    const option = target instanceof HTMLSelectElement ? target.selectedOptions[0] : undefined;
    const base = option?.dataset.url || form.getAttribute("action") || window.location.pathname;
    return new URL(base, window.location.origin);
}

function getUrl(form: HTMLFormElement, target: EventTarget | null): string {
    const url = destination(form, target);
    const params = new URLSearchParams();

    for (const [name, value] of new FormData(form)) {
        if (typeof value !== "string" || value === "") continue;
        params.set(name, value);
    }

    const query = params.toString();
    return url.pathname + (query ? `?${query}` : "") + url.hash;
}

export default function formChange(form: HTMLElement) {
    if (!(form instanceof HTMLFormElement)) return;

    const apply = (target: EventTarget | null) => {
        if (form.method === "post") {
            const url = destination(form, target);
            form.action = url.pathname + url.search + url.hash;
            form.requestSubmit();
            return;
        }

        window.location.href = getUrl(form, target);
    };

    form.addEventListener("change", (event) => {
        if (!shouldSubmit(event.target)) return;
        apply(event.target);
    });
}
