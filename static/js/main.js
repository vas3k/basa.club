const SIDEBAR_BREAKPOINT = 900;

function stylizeExternalLinks() {
    let internal = location.host.replace("www.", "");
    internal = new RegExp(internal, "i");

    const links = [...document.getElementsByTagName("a")];

    links.forEach((link) => {
        if (internal.test(link.host) || !link.host) return;

        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener");

        const domain = link.host.split(":")[0];
        const img = document.createElement("img");
        img.src = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
        img.className = "link-favicon";
        link.insertBefore(img, link.firstChild);
    });
}

function setSidebarOpen(isOpen) {
    document.body.classList.toggle("sidebar-open", isOpen);
    document.querySelector(".header-menu-button")?.setAttribute("aria-expanded", String(isOpen));
}

function closeSidebar() {
    setSidebarOpen(false);
}

function initSidebar() {
    const button = document.querySelector(".header-menu-button");
    const overlay = document.querySelector(".sidebar-overlay");
    const sidebar = document.querySelector(".sidebar");
    if (!button || !sidebar) return;

    button.setAttribute("aria-expanded", "false");
    button.addEventListener("click", () => {
        setSidebarOpen(!document.body.classList.contains("sidebar-open"));
    });

    overlay?.addEventListener("click", closeSidebar);

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeSidebar();
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > SIDEBAR_BREAKPOINT) closeSidebar();
    });
}

const GEO_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

function setCookie(name, value) {
    document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${GEO_COOKIE_MAX_AGE}; samesite=lax`;
}

function initGeoSelects() {
    const form = document.querySelector(".subheader-search");
    if (!form) return;

    const queryInput = form.querySelector("[name=query]");

    form.querySelectorAll("select[data-geo]").forEach((select) => {
        select.addEventListener("change", () => {
            const option = select.selectedOptions[0];
            if (!option) return;

            const countrySelect = form.querySelector("[data-geo=country]");
            const citySelect = form.querySelector("[data-geo=city]");
            setCookie("country", countrySelect?.value || "everywhere");
            setCookie("city", select.dataset.geo === "country" ? "everywhere" : (citySelect?.value || "everywhere"));

            const query = queryInput?.value.trim();
            let url = option.dataset.url || "/";
            if (query) {
                url += `${url.includes("?") ? "&" : "?"}query=${encodeURIComponent(query)}`;
            }
            window.location.href = url;
        });
    });
}

document.addEventListener("DOMContentLoaded", function () {
    stylizeExternalLinks();
    initSidebar();
    initGeoSelects();
});
