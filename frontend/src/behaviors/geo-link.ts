import { rememberGeo } from "../lib/geo";

// <a href="/de/berlin/" data-behavior="geo-link" data-country="de" data-city="berlin">
export default function geoLink(link: HTMLElement) {
    link.addEventListener("click", () => {
        rememberGeo(link.dataset.country || "everywhere", link.dataset.city || "everywhere");
    });
}
