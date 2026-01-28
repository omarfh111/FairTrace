/**
 * ExpandableDrawer - Full Article Detail Panel
 * 
 * Slide-in drawer showing complete citation details.
 * Includes legal disclaimer.
 */

import { RegulationCardIntent } from "./generative-ui.types";
import { FileText, X, BookOpen, AlertTriangle } from "lucide-react";
import { useEffect, useCallback } from "react";

interface ExpandableDrawerProps {
    card: RegulationCardIntent | null;
    isOpen: boolean;
    onClose: () => void;
}

export function ExpandableDrawer({ card, isOpen, onClose }: ExpandableDrawerProps) {
    // Close on Escape key
    const handleKeyDown = useCallback(
        (e: KeyboardEvent) => {
            if (e.key === "Escape" && isOpen) {
                onClose();
            }
        },
        [isOpen, onClose]
    );

    useEffect(() => {
        document.addEventListener("keydown", handleKeyDown);
        return () => document.removeEventListener("keydown", handleKeyDown);
    }, [handleKeyDown]);

    // Prevent body scroll when drawer is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "";
        }
        return () => {
            document.body.style.overflow = "";
        };
    }, [isOpen]);

    return (
        <>
            {/* Overlay */}
            <div
                className={`reg-drawer-overlay ${isOpen ? "open" : ""}`}
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Drawer */}
            <div
                className={`reg-drawer ${isOpen ? "open" : ""}`}
                role="dialog"
                aria-modal="true"
                aria-labelledby="drawer-title"
            >
                <div className="reg-drawer-header">
                    <div className="reg-drawer-title" id="drawer-title">
                        <BookOpen size={20} />
                        <span>Détail de la source</span>
                    </div>
                    <button
                        className="reg-drawer-close"
                        onClick={onClose}
                        aria-label="Fermer"
                    >
                        <X size={18} />
                    </button>
                </div>

                {card && (
                    <div className="reg-drawer-content">
                        {/* Article Info */}
                        <div className="reg-drawer-section">
                            <div className="reg-drawer-section-title">Référence</div>
                            <div className="reg-drawer-article-name">{card.article}</div>
                            <div className="reg-drawer-page-badge">
                                <FileText size={14} />
                                <span>Page {card.page}</span>
                            </div>
                        </div>

                        {/* Full Excerpt */}
                        <div className="reg-drawer-section">
                            <div className="reg-drawer-section-title">Extrait</div>
                            <div className="reg-drawer-excerpt">{card.excerpt}</div>
                        </div>

                        {/* Confidence */}
                        <div className="reg-drawer-section">
                            <div className="reg-drawer-section-title">Niveau de confiance</div>
                            <span
                                className={`reg-answer-badge ${card.confidence.toLowerCase()}`}
                                style={{ display: "inline-block" }}
                            >
                                {card.confidence === "HIGH" && "Confiance élevée"}
                                {card.confidence === "MEDIUM" && "Confiance modérée"}
                                {card.confidence === "LOW" && "Confiance faible"}
                            </span>
                        </div>

                        {/* Legal Disclaimer */}
                        <div className="reg-drawer-section">
                            <div className="reg-drawer-disclaimer">
                                <AlertTriangle size={16} />
                                <span>
                                    <strong>Support d'interprétation</strong> – Ce contenu est fourni à
                                    titre informatif uniquement et ne constitue pas un conseil juridique.
                                    Consultez un expert en conformité BCT pour toute décision réglementaire.
                                </span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </>
    );
}
