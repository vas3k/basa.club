import { setCookie } from "../lib/cookies";

export default function geoLink(link: HTMLElement) {
    link.addEventListener("click", () => {
        const country = link.dataset.country || "everywhere";
        const city = link.dataset.city || "everywhere";
        setCookie("country", country, 31536000);
        setCookie("city", city, 31536000);
    });
}
