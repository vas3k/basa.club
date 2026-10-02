// <button data-behavior="toggle" data-target="#form"> shows/hides the target and focuses its first field.
// With data-mode="show" it never hides, only shows and focuses.
// data-hide-self hides the button once the target is visible.
export default function toggle(button: HTMLElement) {
    button.addEventListener("click", (event) => {
        event.preventDefault();
        const target = document.querySelector<HTMLElement>(button.dataset.target || "");
        if (!target) return;

        target.hidden = button.dataset.mode === "show" ? false : !target.hidden;
        if (!target.hidden) {
            if (button.hasAttribute("data-hide-self")) button.hidden = true;
            target.querySelector<HTMLElement>("input[type=text], textarea, select")?.focus();
        }
    });
}
