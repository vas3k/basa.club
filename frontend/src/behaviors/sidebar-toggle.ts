// Must match the mobile breakpoint in static/css/theme.css and mobile.css.
const SIDEBAR_BREAKPOINT = 739;

export default function sidebarToggle(button: HTMLElement) {
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.querySelector(".sidebar-overlay");
    if (!sidebar) return;

    const setOpen = (isOpen: boolean) => {
        document.body.classList.toggle("sidebar-open", isOpen);
        button.setAttribute("aria-expanded", String(isOpen));
    };

    setOpen(false);
    button.addEventListener("click", () => setOpen(!document.body.classList.contains("sidebar-open")));
    overlay?.addEventListener("click", () => setOpen(false));

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") setOpen(false);
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > SIDEBAR_BREAKPOINT) setOpen(false);
    });
}
