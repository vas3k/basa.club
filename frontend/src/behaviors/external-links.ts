export default function externalLinks(element: HTMLElement) {
    const hostname = location.hostname.replace(/^www\./, "");

    element.querySelectorAll<HTMLAnchorElement>("a").forEach((link) => {
        if (!["http:", "https:"].includes(link.protocol)) return;
        const linkHostname = link.hostname.replace(/^www\./, "");
        if (linkHostname === hostname || linkHostname.endsWith(`.${hostname}`)) return;

        link.setAttribute("target", "_blank");
        link.relList.add("noopener");
        if (link.hasAttribute("data-nofavicon")) return;

        const img = document.createElement("img");
        img.src = `https://www.google.com/s2/favicons?domain=${encodeURIComponent(link.hostname)}&sz=32`;
        img.className = "link-favicon";
        img.alt = "";
        link.insertBefore(img, link.firstChild);
    });
}
