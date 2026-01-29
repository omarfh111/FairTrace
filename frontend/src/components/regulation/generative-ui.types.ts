
import { ChatResponse, ChatCitation } from "@/lib/api";

export type UIIntentType =
    | "ANSWER_SUMMARY"
    | "REGULATION_CARD"
    | "CONFIDENCE_BANNER"
    | "FOLLOW_UP_SUGGESTIONS";

// Base Intent Interface
export interface UIIntent {
    type: UIIntentType;
}

// 1. Answer Summary Intent
export interface AnswerSummaryIntent extends UIIntent {
    type: "ANSWER_SUMMARY";
    text: string;
    processingTimeMs: number;
    citationCount: number;
}

// 2. Regulation Card Intent (for each citation)
export interface RegulationCardIntent extends UIIntent {
    type: "REGULATION_CARD";
    article: string;
    page: number;
    excerpt: string;
    sourceUrl?: string; // Optional metadata
    fullText?: string;  // Optional full text for drawer
}

// 3. Confidence Banner Intent
export interface ConfidenceBannerIntent extends UIIntent {
    type: "CONFIDENCE_BANNER";
    level: "LOW" | "MEDIUM" | "HIGH";
    message: string;
}

// 4. Follow Up Suggestions Intent
export interface FollowUpSuggestionsIntent extends UIIntent {
    type: "FOLLOW_UP_SUGGESTIONS";
    questions: string[];
}

export type GenerativeUIResponse = UIIntent[];

// --- Transformation Logic ---

export function transformResponseToIntents(response: ChatResponse): GenerativeUIResponse {
    const intents: UIIntent[] = [];

    // 1. Answer Summary
    if (response.answer) {
        intents.push({
            type: "ANSWER_SUMMARY",
            text: response.answer,
            processingTimeMs: response.processing_time_ms,
            citationCount: response.citations?.length || 0,
        } as AnswerSummaryIntent);
    }

    // 2. Confidence Banner (only if LOW or MEDIUM)
    if (response.confidence === "LOW" || response.confidence === "MEDIUM") {
        let message = "⚠️ Réponse incertaine. Veuillez vérifier avec le texte officiel.";
        if (response.confidence === "LOW") {
            message = "⚠️ Réponse incertaine. Consultez un expert en conformité BCT.";
        } else if (response.confidence === "MEDIUM") {
            message = "⚠️ Confiance moyenne. Basé sur les extraits disponibles.";
        }

        intents.push({
            type: "CONFIDENCE_BANNER",
            level: response.confidence,
            message,
        } as ConfidenceBannerIntent);
    }

    // 3. Regulation Cards
    if (response.citations && response.citations.length > 0) {
        response.citations.forEach(cit => {
            intents.push({
                type: "REGULATION_CARD",
                article: cit.article,
                page: cit.page,
                excerpt: cit.excerpt,
            } as RegulationCardIntent);
        });
    }

    // 4. Follow Up Suggestions
    if (response.follow_up_questions && response.follow_up_questions.length > 0) {
        intents.push({
            type: "FOLLOW_UP_SUGGESTIONS",
            questions: response.follow_up_questions,
        } as FollowUpSuggestionsIntent);
    }

    return intents;
}

// Helpers to extract specific intents for easier rendering
export function getAnswerSummary(intents: GenerativeUIResponse): AnswerSummaryIntent | undefined {
    return intents.find(i => i.type === "ANSWER_SUMMARY") as AnswerSummaryIntent;
}

export function getConfidenceBanner(intents: GenerativeUIResponse): ConfidenceBannerIntent | undefined {
    return intents.find(i => i.type === "CONFIDENCE_BANNER") as ConfidenceBannerIntent;
}

export function getRegulationCards(intents: GenerativeUIResponse): RegulationCardIntent[] {
    return intents.filter(i => i.type === "REGULATION_CARD") as RegulationCardIntent[];
}

export function getFollowUpSuggestions(intents: GenerativeUIResponse): FollowUpSuggestionsIntent | undefined {
    return intents.find(i => i.type === "FOLLOW_UP_SUGGESTIONS") as FollowUpSuggestionsIntent;
}
