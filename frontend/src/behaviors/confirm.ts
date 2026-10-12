export default function confirmSubmit(form: HTMLElement) {
    form.addEventListener("submit", (event) => {
        if (!window.confirm(form.dataset.confirm || "Вы уверены?")) {
            event.preventDefault();
        }
    });
}
