import { useRef, useState } from "react";

import { isImageFile, uploadImage } from "../lib/upload";

type Props = {
  name: string;
  value?: string;
};

export default function ImageUpload({ name, value = "" }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [url, setUrl] = useState(value);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onChange() {
    const file = input.current?.files?.[0];
    if (!file) return;
    if (!isImageFile(file)) {
      setError("Можно загружать только картинки");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setUrl(await uploadImage(file));
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Не получилось загрузить картинку",
      );
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div className="image-upload">
      <input type="hidden" name={name} value={url} />
      <span className="image-upload-preview">
        {url ? <img src={url} alt="" /> : <span>Картинки</span>}
      </span>
      <label className="image-upload-file">
        <input
          ref={input}
          type="file"
          accept="image/jpeg,image/png,image/bmp,image/webp"
          onChange={onChange}
        />
        {busy ? "Загружаю…" : null}
      </label>
      {error && <div className="form-error">{error}</div>}
    </div>
  );
}
