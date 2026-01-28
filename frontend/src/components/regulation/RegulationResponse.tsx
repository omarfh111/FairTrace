/**
 * RegulationResponse - Main Generative UI Orchestrator
 * 
 * Transforms API response to UI intents and renders all sub-components.
 * This replaces the plain text message rendering for assistant responses.
 */

import { useState } from "react";
import { ChatResponse } from "@/lib/api";
import {
    transformResponseToIntents,
    getAnswerSummary,
    getConfidenceBanner,
    getRegulationCards,
    getFollowUpSuggestions,
    RegulationCardIntent,
} from "./generative-ui.types";
import { AnswerSummaryPanel } from "./AnswerSummaryPanel";
import { ConfidenceBanner } from "./ConfidenceBanner";
import { RegulationCardsGrid } from "./RegulationCard";
import { FollowUpChips } from "./FollowUpChips";
import { ExpandableDrawer } from "./ExpandableDrawer";
import "./GenerativeUIStyles.css";

interface RegulationResponseProps {
    response: ChatResponse;
    onFollowUpClick: (question: string) => void;
}

export function RegulationResponse({
    response,
    onFollowUpClick,
}: RegulationResponseProps) {
    const [selectedCard, setSelectedCard] = useState<RegulationCardIntent | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

    // Transform API response to UI intents
    const uiResponse = transformResponseToIntents(response);

    // Extract intents by type
    const answerSummary = getAnswerSummary(uiResponse);
    const confidenceBanner = getConfidenceBanner(uiResponse);
    const regulationCards = getRegulationCards(uiResponse);
    const followUpSuggestions = getFollowUpSuggestions(uiResponse);

    const handleCardClick = (card: RegulationCardIntent) => {
        setSelectedCard(card);
        setDrawerOpen(true);
    };

    const handleDrawerClose = () => {
        setDrawerOpen(false);
        // Keep selected card for animation, clear after transition
        setTimeout(() => setSelectedCard(null), 300);
    };

    return (
        <div className="reg-response">
            {/* 1. Answer Summary Panel */}
            {answerSummary && (
                <AnswerSummaryPanel
                    intent={answerSummary}
                    confidence={response.confidence}
                />
            )}

            {/* 2. Confidence Banner (only for LOW/MEDIUM) */}
            {confidenceBanner && <ConfidenceBanner intent={confidenceBanner} />}

            {/* 3. Regulation Cards Grid */}
            {regulationCards.length > 0 && (
                <RegulationCardsGrid
                    cards={regulationCards}
                    onCardClick={handleCardClick}
                />
            )}

            {/* 4. Follow-up Question Chips */}
            {followUpSuggestions && (
                <FollowUpChips
                    intent={followUpSuggestions}
                    onChipClick={onFollowUpClick}
                />
            )}

            {/* 5. Expandable Drawer */}
            <ExpandableDrawer
                card={selectedCard}
                isOpen={drawerOpen}
                onClose={handleDrawerClose}
            />
        </div>
    );
}

export default RegulationResponse;
