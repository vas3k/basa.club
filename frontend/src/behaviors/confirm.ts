// <form data-behavior="confirm" data-confirm="Точно удалить?"> asks before submitting
export default function confirmSubmit(form: HTMLElement) {
    form.addEventListener("submit", (event) => {
        if (!window.confirm(form.dataset.confirm || "Вы уверены?")) {
            event.preventDefault();
        }
    });
}
