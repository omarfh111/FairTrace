
import { ConfidenceBannerIntent } from "./generative-ui.types";
import { AlertTriangle } from "lucide-react";

interface Props {
    intent: ConfidenceBannerIntent;
}

export function ConfidenceBanner({ intent }: Props) {
    return (
        <div className={`confidence-banner ${intent.level}`}>
            <AlertTriangle size={18} />
            <span>{intent.message}</span>
        </div>
    );
}
