import { useState } from "react";

import { postJson } from "../lib/http";

type Props = {
    upvotes: number;
    voted: boolean;
    upvoteUrl: string;
    retractUrl: string;
    loginUrl?: string | null;
    disabled?: boolean;
    // block: big arrow + counter (items), inline: "label N" (comments), tiny: "+ N" (replies)
    variant?: "block" | "inline" | "tiny";
    label?: string;
};

type VoteResponse = {
    upvotes: number;
    voted: boolean;
};

export default function UpvoteButton({
    upvotes,
    voted,
    upvoteUrl,
    retractUrl,
    loginUrl,
    disabled,
    variant = "block",
    label,
}: Props) {
    const [state, setState] = useState({ upvotes, voted });
    const [isPending, setIsPending] = useState(false);

    async function toggle() {
        if (loginUrl) {
            window.location.href = `${loginUrl}?next=${encodeURIComponent(location.pathname)}`;
            return;
        }
        if (isPending) return;

        const previous = state;
        const voting = !state.voted;
        setState({ upvotes: state.upvotes + (voting ? 1 : -1), voted: voting });
        setIsPending(true);

        try {
            setState(await postJson<VoteResponse>(voting ? upvoteUrl : retractUrl));
        } catch (error) {
            console.error("Vote failed", error);
            setState(previous);
        } finally {
            setIsPending(false);
        }
    }

    const classNames = ["upvote", `upvote-${variant}`, state.voted ? "upvote-voted" : ""].filter(Boolean).join(" ");

    return (
        <button
            type="button"
            className={classNames}
            disabled={disabled}
            aria-pressed={state.voted}
            title={disabled ? "Голоса" : state.voted ? "Забрать голос" : "Проголосовать"}
            onClick={toggle}
        >
            {variant === "block" && <i className="fas fa-chevron-up upvote-arrow" />}
            {variant === "tiny" && <i className="fas fa-plus upvote-arrow" />}
            {variant === "inline" && label && <span className="upvote-label">{label}</span>}
            <span className="upvote-count">{state.upvotes}</span>
        </button>
    );
}
