/**
 * Generative UI Types and Transformation Layer
 * 
 * Converts API responses to typed UI intents for structured rendering.
 */

import { ChatCitation, ChatResponse } from "@/lib/api";

// =============================================================================
// UI INTENT TYPES
// =============================================================================

export type ConfidenceLevel = "LOW" | "MEDIUM" | "HIGH";

export interface AnswerSummaryIntent {
    type: "ANSWER_SUMMARY";
    text: string;
    processingTimeMs: number;
    citationCount: number;
}

export interface RegulationCardIntent {
    type: "REGULATION_CARD";
    id: string;
    article: string;
    excerpt: string;
    page: number;
    confidence: ConfidenceLevel;
}

export interface ConfidenceBannerIntent {
    type: "CONFIDENCE_BANNER";
    level: "LOW" | "MEDIUM";
    message: string;
}

export interface FollowUpIntent {
    type: "FOLLOW_UP_SUGGESTIONS";
    questions: string[];
}

export type UIIntent =
    | AnswerSummaryIntent
    | RegulationCardIntent
    | ConfidenceBannerIntent
    | FollowUpIntent;

export interface GenerativeUIResponse {
    intents: UIIntent[];
    conversationId: string;
    timestamp: Date;
}

// =============================================================================
// TRANSFORMATION FUNCTION
// =============================================================================

/**
 * Transform a chat API response into UI intents for structured rendering.
 * 
 * The order of intents determines rendering order:
 * 1. Answer Summary Panel
 * 2. Confidence Banner (if LOW/MEDIUM)
 * 3. Regulation Cards (one per citation)
 * 4. Follow-up Question Chips
 */
export function transformResponseToIntents(
    response: ChatResponse
): GenerativeUIResponse {
    const intents: UIIntent[] = [];

    // 1. Answer Summary Intent
    intents.push({
        type: "ANSWER_SUMMARY",
        text: response.answer,
        processingTimeMs: response.processing_time_ms,
        citationCount: response.citations?.length ?? 0,
    });

    // 2. Confidence Banner (only for LOW or MEDIUM)
    if (response.confidence === "LOW" || response.confidence === "MEDIUM") {
        const message =
            response.confidence === "LOW"
                ? "⚠️ Réponse incertaine. Consultez un expert en conformité BCT."
                : "⚡ Confiance modérée. Vérifiez les sources pour plus de précision.";

        intents.push({
            type: "CONFIDENCE_BANNER",
            level: response.confidence,
            message,
        });
    }

    // 3. Regulation Cards (one per citation)
    if (response.citations && response.citations.length > 0) {
        response.citations.forEach((citation, index) => {
            intents.push({
                type: "REGULATION_CARD",
                id: `reg-${index}`,
                article: citation.article || `Document - Page ${citation.page}`,
                excerpt: citation.excerpt,
                page: citation.page,
                confidence: response.confidence,
            });
        });
    }

    // 4. Follow-up Suggestions
    if (response.follow_up_questions && response.follow_up_questions.length > 0) {
        intents.push({
            type: "FOLLOW_UP_SUGGESTIONS",
            questions: response.follow_up_questions,
        });
    }

    return {
        intents,
        conversationId: response.conversation_id,
        timestamp: new Date(),
    };
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

export function getIntentsByType<T extends UIIntent["type"]>(
    response: GenerativeUIResponse,
    type: T
): Extract<UIIntent, { type: T }>[] {
    return response.intents.filter((intent) => intent.type === type) as Extract<
        UIIntent,
        { type: T }
    >[];
}

export function getAnswerSummary(
    response: GenerativeUIResponse
): AnswerSummaryIntent | undefined {
    return getIntentsByType(response, "ANSWER_SUMMARY")[0];
}

export function getConfidenceBanner(
    response: GenerativeUIResponse
): ConfidenceBannerIntent | undefined {
    return getIntentsByType(response, "CONFIDENCE_BANNER")[0];
}

export function getRegulationCards(
    response: GenerativeUIResponse
): RegulationCardIntent[] {
    return getIntentsByType(response, "REGULATION_CARD");
}

export function getFollowUpSuggestions(
    response: GenerativeUIResponse
): FollowUpIntent | undefined {
    return getIntentsByType(response, "FOLLOW_UP_SUGGESTIONS")[0];
}
