/**
 * ConfidenceBanner - Warning Banner for LOW/MEDIUM Confidence
 * 
 * Only renders when confidence is not HIGH.
 */

import { ConfidenceBannerIntent } from "./generative-ui.types";
import { AlertTriangle, AlertCircle } from "lucide-react";

interface ConfidenceBannerProps {
    intent: ConfidenceBannerIntent;
}

export function ConfidenceBanner({ intent }: ConfidenceBannerProps) {
    return (
        <div className={`reg-confidence-banner ${intent.level.toLowerCase()}`}>
            {intent.level === "LOW" ? (
                <AlertCircle size={18} />
            ) : (
                <AlertTriangle size={18} />
            )}
            <span>{intent.message}</span>
        </div>
    );
}
