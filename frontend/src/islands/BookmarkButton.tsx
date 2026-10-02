import { useState } from "react";

import { postJson } from "../lib/http";

type Props = {
    bookmarkCount: number;
    bookmarkUrl: string;
    loginUrl?: string | null;
};

type BookmarkResponse = {
    bookmark_count: number;
};

export default function BookmarkButton({ bookmarkCount, bookmarkUrl, loginUrl }: Props) {
    const [count, setCount] = useState(bookmarkCount);
    const [isPending, setIsPending] = useState(false);

    async function toggle() {
        if (loginUrl) {
            window.location.href = `${loginUrl}?next=${encodeURIComponent(location.pathname + location.search)}`;
            return;
        }
        if (isPending) return;

        setIsPending(true);
        try {
            const data = await postJson<BookmarkResponse>(bookmarkUrl);
            setCount(data.bookmark_count);
        } catch (error) {
            console.error("Bookmark failed", error);
        } finally {
            setIsPending(false);
        }
    }

    return (
        <button
            type="button"
            className="item-action"
            disabled={isPending}
            title="Закладка"
            aria-label="Закладка"
            onClick={toggle}
        >
            <i className="far fa-star" />
            <span className="item-action-count">{count}</span>
        </button>
    );
}
