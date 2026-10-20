export default function noEnterSubmit(form: HTMLElement) {
    if (!(form instanceof HTMLFormElement)) return;

    form.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        if (event.target instanceof HTMLTextAreaElement) return;
        if (!(event.target instanceof HTMLInputElement)) return;
        event.preventDefault();
    });
}
