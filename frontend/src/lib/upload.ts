import { csrfToken } from "./http";

export async function uploadImage(file: File): Promise<string> {
    const body = new FormData();
    body.append("media", file);
    const response = await fetch("/api/images/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
            Accept: "application/json",
            "X-CSRFToken": csrfToken(),
        },
        body,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || typeof data.url !== "string") {
        throw new Error(data.error || "Не получилось загрузить картинку");
    }
    return data.url;
}
