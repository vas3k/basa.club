export default function noEnterSubmit(form: HTMLElement) {
    if (!(form instanceof HTMLFormElement)) return;

    // iOS Return activates the first submit button (draft) and may skip the key event entirely.
    let buttonPressed = false;
    const submitButton = "button[type=submit], input[type=submit]";

    form.addEventListener("pointerdown", (event) => {
        if (event.target instanceof Element && event.target.closest(submitButton)) buttonPressed = true;
    });
    form.addEventListener("pointercancel", () => {
        buttonPressed = false;
    });

    form.addEventListener("keydown", (event) => {
        const target = event.target;
        // A textarea, and the markdown editor on mobile, use Enter for a new line.
        if (target instanceof HTMLTextAreaElement) return;
        if (target instanceof HTMLElement && target.isContentEditable) return;

        const onButton = target instanceof HTMLButtonElement && target.type === "submit";
        if (onButton && (event.key === "Enter" || event.key === " ")) {
            buttonPressed = true;
            return;
        }
        if (event.key !== "Enter") return;

        buttonPressed = false;
        if (target instanceof HTMLInputElement || target instanceof HTMLSelectElement) event.preventDefault();
    });

    form.addEventListener("submit", (event) => {
        if (buttonPressed) {
            buttonPressed = false;
            return;
        }
        event.preventDefault();
    });
}
