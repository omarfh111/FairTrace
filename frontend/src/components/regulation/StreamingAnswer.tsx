/**
 * StreamingAnswer - Real-time Streaming Response Component
 * 
 * Displays the agent's answer with a cool typing animation effect,
 * then reveals citations one by one with staggered animation.
 */

import { useState, useEffect, useRef } from "react";
import { ChatCitation } from "../../lib/api";
import { Clock, FileText, Loader2, BookOpen, ChevronRight, AlertTriangle, Search } from "lucide-react";
import "./StreamingAnswer.css";

interface StreamingAnswerProps {
    status: "idle" | "searching" | "analyzing" | "streaming" | "citations" | "done";
    statusMessage: string;
    streamedText: string;
    citations: (ChatCitation & { index: number })[];
    metadata: {
        confidence: "LOW" | "MEDIUM" | "HIGH";
        processingTimeMs: number;
        citationsCount: number;
        followUpQuestions: string[];
    } | null;
    onCitationClick?: (citation: ChatCitation) => void;
    onFollowUpClick?: (question: string) => void;
}

export function StreamingAnswer({
    status,
    statusMessage,
    streamedText,
    citations,
    metadata,
    onCitationClick,
    onFollowUpClick
}: StreamingAnswerProps) {
    const textRef = useRef<HTMLDivElement>(null);
    const [showCursor, setShowCursor] = useState(true);

    // Blinking cursor effect during streaming
    useEffect(() => {
        if (status === "streaming") {
            const interval = setInterval(() => {
                setShowCursor(prev => !prev);
            }, 530);
            return () => clearInterval(interval);
        } else {
            setShowCursor(false);
        }
    }, [status]);

    // Auto-scroll during streaming
    useEffect(() => {
        if (textRef.current && status === "streaming") {
            textRef.current.scrollTop = textRef.current.scrollHeight;
        }
    }, [streamedText, status]);

    const isLoading = status === "searching" || status === "analyzing";
    const isStreaming = status === "streaming";
    const isDone = status === "done";

    // Status icons
    const StatusIcon = () => {
        if (status === "searching") return <Search className="animate-pulse" />;
        if (status === "analyzing") return <Loader2 className="animate-spin" />;
        if (status === "streaming") return <FileText />;
        return <BookOpen />;
    };

    return (
        <div className="streaming-answer">
            {/* Status Indicator */}
            {(isLoading || isStreaming) && (
                <div className={`streaming-status ${status}`}>
                    <div className="status-icon">
                        <StatusIcon />
                    </div>
                    <span className="status-text">{statusMessage}</span>
                    <div className="status-wave">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            )}

            {/* Answer Panel */}
            {(streamedText || isDone) && (
                <div className="streaming-panel">
                    {/* Header with metadata */}
                    {metadata && (
                        <div className="streaming-header">
                            <div className="streaming-meta">
                                <div className="meta-item">
                                    <Clock size={14} />
                                    <span>{(metadata.processingTimeMs / 1000).toFixed(1)}s</span>
                                </div>
                                <div className="meta-item">
                                    <FileText size={14} />
                                    <span>{metadata.citationsCount} source{metadata.citationsCount !== 1 ? 's' : ''}</span>
                                </div>
                            </div>
                            <span className={`confidence-badge ${metadata.confidence.toLowerCase()}`}>
                                {metadata.confidence === "HIGH" && "Confiance élevée"}
                                {metadata.confidence === "MEDIUM" && "Confiance modérée"}
                                {metadata.confidence === "LOW" && "Confiance faible"}
                            </span>
                        </div>
                    )}

                    {/* Confidence Warning Banner */}
                    {metadata && (metadata.confidence === "LOW" || metadata.confidence === "MEDIUM") && (
                        <div className={`confidence-banner ${metadata.confidence.toLowerCase()}`}>
                            <AlertTriangle size={16} />
                            <span>
                                {metadata.confidence === "LOW"
                                    ? "⚠️ Réponse incertaine. Consultez un expert en conformité BCT."
                                    : "Vérifiez les sources pour confirmation."}
                            </span>
                        </div>
                    )}

                    {/* Streaming Text */}
                    <div className="streaming-text" ref={textRef}>
                        {streamedText}
                        {isStreaming && (
                            <span className={`typing-cursor ${showCursor ? 'visible' : ''}`}>▌</span>
                        )}
                    </div>
                </div>
            )}

            {/* Citations Grid */}
            {citations.length > 0 && (
                <div className="streaming-citations">
                    <div className="citations-header">
                        <BookOpen size={14} />
                        <span>SOURCES RÉGLEMENTAIRES ({citations.length})</span>
                    </div>
                    <div className="citations-grid">
                        {citations.map((citation, i) => (
                            <div
                                key={i}
                                className="citation-card"
                                style={{ animationDelay: `${i * 100}ms` }}
                                onClick={() => onCitationClick?.(citation)}
                            >
                                <div className="citation-header">
                                    <div className="citation-article">
                                        <BookOpen size={14} />
                                        <span>{citation.article || `Source ${i + 1}`}</span>
                                    </div>
                                    <span className="citation-page">p. {citation.page}</span>
                                </div>
                                <p className="citation-excerpt">"{citation.excerpt}"</p>
                                <div className="citation-footer">
                                    <span className="citation-badge">FIABLE</span>
                                    <span className="citation-expand">
                                        Voir plus <ChevronRight size={12} />
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Follow-up Suggestions */}
            {metadata && metadata.followUpQuestions.length > 0 && isDone && (
                <div className="streaming-followups">
                    <span className="followups-label">QUESTIONS CONNEXES</span>
                    <div className="followups-chips">
                        {metadata.followUpQuestions.map((question, i) => (
                            <button
                                key={i}
                                className="followup-chip"
                                onClick={() => onFollowUpClick?.(question)}
                            >
                                {question.length > 45 ? question.slice(0, 45) + '...' : question}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default StreamingAnswer;
