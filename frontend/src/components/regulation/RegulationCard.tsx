/**
 * RegulationCard - Citation Card Component
 * 
 * Glassmorphic card displaying a single regulation citation.
 * Clickable to open the ExpandableDrawer with full details.
 */

import { RegulationCardIntent } from "./generative-ui.types";
import { FileText, ChevronRight } from "lucide-react";

interface RegulationCardProps {
    intent: RegulationCardIntent;
    onClick: (intent: RegulationCardIntent) => void;
}

export function RegulationCard({ intent, onClick }: RegulationCardProps) {
    return (
        <div
            className="reg-card"
            onClick={() => onClick(intent)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                    onClick(intent);
                }
            }}
        >
            <div className="reg-card-header">
                <div className="reg-card-article">
                    <FileText />
                    <span>{intent.article}</span>
                </div>
                <span className="reg-card-page">p. {intent.page}</span>
            </div>

            <div className="reg-card-excerpt">
                "{intent.excerpt}"
            </div>

            <div className="reg-card-footer">
                <span className={`reg-card-confidence ${intent.confidence.toLowerCase()}`}>
                    {intent.confidence === "HIGH" && "Fiable"}
                    {intent.confidence === "MEDIUM" && "Modéré"}
                    {intent.confidence === "LOW" && "Incertain"}
                </span>
                <span className="reg-card-expand">
                    Voir plus <ChevronRight />
                </span>
            </div>
        </div>
    );
}

interface RegulationCardsGridProps {
    cards: RegulationCardIntent[];
    onCardClick: (intent: RegulationCardIntent) => void;
}

export function RegulationCardsGrid({ cards, onCardClick }: RegulationCardsGridProps) {
    if (cards.length === 0) return null;

    return (
        <div className="reg-cards-container">
            <div className="reg-cards-header">
                <FileText />
                <span>Sources réglementaires ({cards.length})</span>
            </div>
            <div className="reg-cards-grid">
                {cards.map((card) => (
                    <RegulationCard
                        key={card.id}
                        intent={card}
                        onClick={onCardClick}
                    />
                ))}
            </div>
        </div>
    );
}
