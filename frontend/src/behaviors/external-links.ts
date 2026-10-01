// Opens external links in a new tab and prepends their favicon
export default function externalLinks(element: HTMLElement) {
    const internal = new RegExp(location.host.replace("www.", ""), "i");

    element.querySelectorAll<HTMLAnchorElement>("a").forEach((link) => {
        if (!link.host || internal.test(link.host)) return;

        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener");

        const domain = link.host.split(":")[0];
        const img = document.createElement("img");
        img.src = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
        img.className = "link-favicon";
        link.insertBefore(img, link.firstChild);
    });
}
