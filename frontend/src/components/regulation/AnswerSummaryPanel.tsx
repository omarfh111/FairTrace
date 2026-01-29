
import { AnswerSummaryIntent } from "./generative-ui.types";

interface Props {
    intent: AnswerSummaryIntent;
    confidence?: string;
}

export function AnswerSummaryPanel({ intent }: Props) {
    return (
        <div className="answer-summary-panel">
            <div className="answer-header">
                <span className="summary-label">Résumé Exécutif</span>
                <div className="answer-meta">
                    <span>{intent.citationCount} Citations</span>
                    <span>{Math.round(intent.processingTimeMs)}ms</span>
                </div>
            </div>
            <div className="answer-text">
                {intent.text}
            </div>
        </div>
    );
}
