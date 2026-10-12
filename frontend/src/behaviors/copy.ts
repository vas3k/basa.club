export default function copy(element: HTMLElement) {
    let timer = 0;

    element.addEventListener("click", async (event) => {
        event.preventDefault();
        const text = element.dataset.copy ?? "";
        if (!text) return;

        let copied = false;
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(text);
                copied = true;
            }
        } catch {
            // Clipboard API can reject without a permission prompt. Try the fallback.
        }

        if (!copied) {
            const area = document.createElement("textarea");
            area.value = text;
            area.setAttribute("readonly", "");
            area.style.position = "fixed";
            area.style.left = "-9999px";
            document.body.appendChild(area);
            try {
                area.select();
                copied = document.execCommand("copy");
            } catch {
                return;
            } finally {
                area.remove();
            }
        }
        if (!copied) return;

        element.dataset.copied = "";
        window.clearTimeout(timer);
        timer = window.setTimeout(() => {
            delete element.dataset.copied;
        }, 1500);
    });
}
