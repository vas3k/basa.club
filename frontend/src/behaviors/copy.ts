// <button data-behavior="copy" data-copy="text"> copies data-copy and sets data-copied for a moment.

export default function copy(element: HTMLElement) {
    let timer = 0;

    element.addEventListener("click", async (event) => {
        event.preventDefault();
        const text = element.dataset.copy ?? "";
        if (!text) return;

        try {
            await writeClipboard(text);
        } catch {
            return;
        }

        element.dataset.copied = "";
        window.clearTimeout(timer);
        timer = window.setTimeout(() => {
            delete element.dataset.copied;
        }, 1500);
    });
}

async function writeClipboard(text: string) {
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
            return;
        }
    } catch {
        // Clipboard API can reject without a permission prompt. Fall through.
    }

    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    const copied = document.execCommand("copy");
    area.remove();
    if (!copied) throw new Error("copy failed");
}
