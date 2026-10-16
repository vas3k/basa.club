import { useState } from "react";

import { HttpError, postJson } from "../lib/http";

type Props = {
    rating: string;
    voted: boolean;
    upvoteUrl: string;
    retractUrl: string;
    loginUrl?: string | null;
    disabled?: boolean;
};

type VoteResponse = {
    rating: string;
    voted: boolean;
};

export default function ItemUpvote({ rating, voted, upvoteUrl, retractUrl, loginUrl, disabled }: Props) {
    const [state, setState] = useState({ rating, voted });
    const [isPending, setIsPending] = useState(false);
    const [notice, setNotice] = useState<string | null>(null);
    const canToggle = !disabled || state.voted;

    async function toggle() {
        if (loginUrl) {
            window.location.href = loginUrl;
            return;
        }
        if (!canToggle || isPending) return;

        const previous = state;
        const voting = !state.voted;
        setState({ ...state, voted: voting });
        setIsPending(true);

        try {
            const data = await postJson<VoteResponse>(voting ? upvoteUrl : retractUrl);
            setState({ rating: data.rating, voted: data.voted });
            setNotice(null);
        } catch (error) {
            console.error("Vote failed", error);
            setState(previous);
            setNotice(error instanceof HttpError ? error.message : "Не получилось проголосовать");
        } finally {
            setIsPending(false);
        }
    }

    const shown = Number.parseFloat(state.rating);
    let tone = "rating-zero";
    if (shown > 0 || (state.voted && shown < 0)) {
        tone = "rating-positive";
    } else if (shown < 0) {
        tone = "rating-negative";
    }

    const className = state.voted ? `item-upvote ${tone} is-voted` : `item-upvote ${tone}`;

    return (
        <button
            type="button"
            className={className}
            disabled={!canToggle || isPending}
            aria-pressed={state.voted}
            title={notice || (!canToggle ? "Рейтинг" : state.voted ? "Забрать голос" : "Проголосовать")}
            onClick={toggle}
        >
            <span className="item-upvote-rating">{state.rating}</span>
            <i className="fas fa-caret-up" />
        </button>
    );
}
