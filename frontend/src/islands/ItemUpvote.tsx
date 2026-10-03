import { useState } from "react";

import { postJson } from "../lib/http";

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
        } catch (error) {
            console.error("Vote failed", error);
            setState(previous);
        } finally {
            setIsPending(false);
        }
    }

    return (
        <button
            type="button"
            className={state.voted ? "item-upvote is-voted" : "item-upvote"}
            disabled={!canToggle || isPending}
            aria-pressed={state.voted}
            title={!canToggle ? "Рейтинг" : state.voted ? "Забрать голос" : "Проголосовать"}
            onClick={toggle}
        >
            <span className="item-upvote-rating">{state.rating}</span>
            <i className="fas fa-caret-up" />
        </button>
    );
}
