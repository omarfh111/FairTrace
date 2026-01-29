
import { FollowUpSuggestionsIntent } from "./generative-ui.types";
import { MessageCircle } from "lucide-react";

interface Props {
    intent: FollowUpSuggestionsIntent;
    onChipClick: (question: string) => void;
}

export function FollowUpChips({ intent, onChipClick }: Props) {
    return (
        <div className="follow-up-container">
            {intent.questions.map((question, index) => (
                <button
                    key={index}
                    className="follow-up-chip"
                    onClick={() => onChipClick(question)}
                >
                    {question}
                </button>
            ))}
        </div>
    );
}
