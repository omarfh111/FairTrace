/**
 * AnswerSummaryPanel - Executive Summary Component
 * 
 * Displays the agent's answer with metadata in a professional panel.
 * Renders clean prose text without markdown formatting.
 */

import { AnswerSummaryIntent, ConfidenceLevel } from "./generative-ui.types";
import { Clock, FileText } from "lucide-react";

/**
 * Strip markdown formatting from text to display as clean prose.
 * Handles: **bold**, *italic*, ## headers, bullet points, etc.
 */
function stripMarkdown(text: string): string {
    return text
        // Remove headers (## Header)
        .replace(/^#{1,6}\s+/gm, "")
        // Remove bold/italic (**text** or *text* or __text__ or _text_)
        .replace(/\*\*([^*]+)\*\*/g, "$1")
        .replace(/\*([^*]+)\*/g, "$1")
        .replace(/__([^_]+)__/g, "$1")
        .replace(/_([^_]+)_/g, "$1")
        // Remove bullet points at start of lines (- item or * item)
        .replace(/^[\s]*[-*+]\s+/gm, "")
        // Remove numbered lists formatting but keep the number (1. item -> 1. item)
        .replace(/^(\d+)\.\s+/gm, "$1. ")
        // Remove code blocks
        .replace(/```[\s\S]*?```/g, "")
        .replace(/`([^`]+)`/g, "$1")
        // Remove horizontal rules
        .replace(/^[-*_]{3,}\s*$/gm, "")
        // Clean up extra whitespace
        .replace(/\n{3,}/g, "\n\n")
        .trim();
}

interface AnswerSummaryPanelProps {
    intent: AnswerSummaryIntent;
    confidence: ConfidenceLevel;
}

export function AnswerSummaryPanel({ intent, confidence }: AnswerSummaryPanelProps) {
    // Strip any markdown from the answer text
    const cleanText = stripMarkdown(intent.text);

    return (
        <div className="reg-answer-summary">
            <div className="reg-answer-header">
                <div className="reg-answer-meta">
                    <div className="reg-answer-meta-item">
                        <Clock />
                        <span>{(intent.processingTimeMs / 1000).toFixed(1)}s</span>
                    </div>
                    <div className="reg-answer-meta-item">
                        <FileText />
                        <span>{intent.citationCount} source{intent.citationCount !== 1 ? 's' : ''}</span>
                    </div>
                </div>
                <span className={`reg-answer-badge ${confidence.toLowerCase()}`}>
                    {confidence === "HIGH" && "Confiance élevée"}
                    {confidence === "MEDIUM" && "Confiance modérée"}
                    {confidence === "LOW" && "Confiance faible"}
                </span>
            </div>
            <div className="reg-answer-text">
                {cleanText}
            </div>
        </div>
    );
}
