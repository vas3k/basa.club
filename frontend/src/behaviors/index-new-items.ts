import { setCookie } from "../lib/cookies";

export default function indexNewItems(index: HTMLElement) {
    const now = Date.now();
    const cookie = document.cookie.split("; ").find((value) => value.startsWith("last_visit="));
    const lastVisit = Number(cookie?.slice("last_visit=".length));

    if (Number.isFinite(lastVisit) && lastVisit > 0 && lastVisit <= now) {
        index.querySelectorAll<HTMLElement>(".index-card[data-published-at]").forEach((card) => {
            const publishedAt = Date.parse(card.dataset.publishedAt || "");
            if (publishedAt <= lastVisit || publishedAt > now || !Number.isFinite(publishedAt)) return;

            card.classList.add("is-new");
            const badge = card.querySelector<HTMLElement>(".index-card-new");
            if (badge) badge.hidden = false;
        });
    }

    setCookie("last_visit", String(now), 60 * 60 * 24 * 365);
}
