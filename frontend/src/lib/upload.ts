import { csrfToken } from "./http";

const ACCEPT = ["image/jpeg", "image/png", "image/bmp", "image/webp", "image/jpg"];

export function isImageFile(file: File): boolean {
    if (ACCEPT.includes(file.type)) return true;
    return /\.(jpe?g|png|bmp|webp)$/i.test(file.name);
}

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
