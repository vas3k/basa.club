import { csrfToken } from "./http";

const imageExtensions = new Set(["jpg", "jpeg", "png", "gif", "webp"]);
const imageTypes = new Set(["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]);

export const imageAccept = "image/jpeg,image/png,image/gif,image/webp,.jpg,.jpeg,.png,.gif,.webp";

export const imageTypeError = "Можно загрузить только картинки JPG, PNG, GIF или WebP";

export function isSupportedImage(file: File): boolean {
    const extension = file.name.includes(".") ? file.name.split(".").pop()?.toLowerCase() ?? "" : "";
    if (!imageExtensions.has(extension)) return false;
    const type = file.type.toLowerCase();
    if (type && type !== "application/octet-stream" && !imageTypes.has(type)) return false;
    return true;
}

export async function uploadImage(file: File): Promise<string> {
    if (!isSupportedImage(file)) {
        throw new Error(imageTypeError);
    }
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
