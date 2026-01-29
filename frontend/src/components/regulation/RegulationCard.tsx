
import { RegulationCardIntent } from "./generative-ui.types";
import { ArrowRight, BookOpen } from "lucide-react";

interface GridProps {
    cards: RegulationCardIntent[];
    onCardClick: (card: RegulationCardIntent) => void;
}

export function RegulationCardsGrid({ cards, onCardClick }: GridProps) {
    return (
        <div className="reg-cards-grid">
            {cards.map((card, index) => (
                <div
                    key={index}
                    className="reg-card"
                    onClick={() => onCardClick(card)}
                >
                    <div className="reg-card-header">
                        <span className="article-badge">{card.article}</span>
                        <span className="page-badge">Page {card.page}</span>
                    </div>

                    <div className="reg-card-excerpt">
                        "{card.excerpt}"
                    </div>

                    <div className="reg-card-footer">
                        <span>Voir le contexte</span>
                        <ArrowRight size={14} style={{ marginLeft: '4px' }} />
                    </div>
                </div>
            ))}
        </div>
    );
}
