// Close button on the index welcome letter. Hides it for good:
// a cookie for this browser, and a metadata flag when the reader is logged in.

import { setCookie } from "../lib/cookies";
import { postJson } from "../lib/http";

export default function welcomeClose(button: HTMLElement) {
  button.addEventListener("click", () => {
    const block = button.closest<HTMLElement>(".welcome");
    const flagUrl = button.dataset.flagUrl;
    setCookie("is_welcome_read", "1", 60 * 24 * 365 * 10);
    block?.remove();

    if (!flagUrl) return;
    postJson(flagUrl, { flag: "is_welcome_read", value: true }).catch(() => {});
  });
}
