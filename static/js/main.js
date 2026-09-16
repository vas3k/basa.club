// External links styling
function stylizeExternalLinks() {
    let internal = location.host.replace("www.", "");
    internal = new RegExp(internal, "i");

    const links = [...document.getElementsByTagName("a")];

    links.forEach((link) => {
        if (internal.test(link.host) || !link.host) return;

        // open external link in new tab
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener");

        // insert favicon img
        const domain = link.host.split(":")[0];
        const img = document.createElement("img");
        img.src = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
        img.className = "link-favicon";
        link.insertBefore(img, link.firstChild);
    });
}


// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    stylizeExternalLinks();
});
