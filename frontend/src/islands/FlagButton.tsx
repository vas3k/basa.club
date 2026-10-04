import { useEffect, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";

import { HttpError, postJson } from "../lib/http";

type Reason = {
  value: string;
  label: string;
};

type Props = {
  flagUrl: string;
  loginUrl?: string | null;
  commentMaxLength: number;
  reasons: Reason[];
};

export default function FlagButton({
  flagUrl,
  loginUrl,
  commentMaxLength,
  reasons,
}: Props) {
  const [draftReason, setDraftReason] = useState("");
  const [draftComment, setDraftComment] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen]);

  function open() {
    if (loginUrl) {
      window.location.href = loginUrl;
      return;
    }
    setDraftReason("");
    setDraftComment("");
    setError("");
    setIsSent(false);
    setIsOpen(true);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!draftReason || isPending) return;

    setIsPending(true);
    setError("");
    try {
      await postJson(flagUrl, {
        reason: draftReason,
        comment: draftComment,
      });
      setIsSent(true);
    } catch (caught) {
      setError(
        caught instanceof HttpError
          ? caught.message
          : "Не получилось отправить",
      );
    } finally {
      setIsPending(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="inline-block item-action item-action-icon"
        title="Пожаловаться"
        aria-label="Пожаловаться"
        onClick={open}
      >
        <i className="far fa-flag" />
      </button>
      {isOpen &&
        createPortal(
          <div className="flag-popup-backdrop" onClick={() => setIsOpen(false)}>
            <form
              className="flag-popup"
              onClick={(event) => event.stopPropagation()}
              onSubmit={submit}
            >
              {isSent ? (
                <>
                  <div className="flag-popup-title">Жалоба отправлена</div>
                  <div className="flag-popup-actions">
                    <button
                      type="button"
                      className="button button-small"
                      onClick={() => setIsOpen(false)}
                    >
                      Спасибо 🙏
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="flag-popup-title">Пожаловаться</div>
                  <div className="flag-popup-reasons">
                    {reasons.map((option) => (
                      <label className="flag-popup-reason" key={option.value}>
                        <input
                          type="radio"
                          name={flagUrl}
                          value={option.value}
                          checked={draftReason === option.value}
                          onChange={() => setDraftReason(option.value)}
                        />
                        {option.label}
                      </label>
                    ))}
                  </div>
                  <textarea
                    className="flag-popup-comment"
                    value={draftComment}
                    maxLength={commentMaxLength}
                    placeholder="Комментарий..."
                    onChange={(event) => setDraftComment(event.target.value)}
                  />
                  {error && <div className="flag-popup-error">{error}</div>}
                  <div className="flag-popup-actions">
                    <button
                      type="button"
                      className="button button-small button-inverted"
                      onClick={() => setIsOpen(false)}
                    >
                      Отмена
                    </button>
                    <button
                      type="submit"
                      className="button button-small"
                      disabled={!draftReason || isPending}
                    >
                      Отправить
                    </button>
                  </div>
                </>
              )}
            </form>
          </div>,
          document.body,
        )}
    </>
  );
}
