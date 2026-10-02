export default function gallery(element: HTMLElement) {
    element.querySelectorAll<HTMLAnchorElement>("a").forEach((link) => {
        const img = link.querySelector("img");
        if (!img) return;
        const setSize = () => {
            link.dataset.pswpWidth = String(img.naturalWidth || 1200);
            link.dataset.pswpHeight = String(img.naturalHeight || 1200);
        };
        if (img.complete) setSize();
        else img.addEventListener("load", setSize);
    });

    void import("photoswipe/lightbox").then(async ({ default: PhotoSwipeLightbox }) => {
        await import("photoswipe/style.css");
        const lightbox = new PhotoSwipeLightbox({
            gallery: element,
            children: "a",
            pswpModule: () => import("photoswipe"),
        });
        lightbox.init();
    });
}
