/**
 * FollowUpChips - Clickable Question Suggestions
 * 
 * Horizontal chips for follow-up questions.
 * Clicking a chip triggers the onChipClick callback.
 */

import { FollowUpIntent } from "./generative-ui.types";

interface FollowUpChipsProps {
    intent: FollowUpIntent;
    onChipClick: (question: string) => void;
}

export function FollowUpChips({ intent, onChipClick }: FollowUpChipsProps) {
    if (intent.questions.length === 0) return null;

    return (
        <div className="reg-followup-container">
            <div className="reg-followup-label">Questions connexes</div>
            <div className="reg-followup-chips">
                {intent.questions.map((question, index) => (
                    <button
                        key={index}
                        className="reg-followup-chip"
                        onClick={() => onChipClick(question)}
                        title={question}
                    >
                        {question.length > 50 ? question.slice(0, 50) + "..." : question}
                    </button>
                ))}
            </div>
        </div>
    );
}
