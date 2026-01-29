
import { RegulationCardIntent } from "./generative-ui.types";
import { X, BookOpen, AlertCircle } from "lucide-react";
import { useEffect } from "react";

interface Props {
    card: RegulationCardIntent | null;
    isOpen: boolean;
    onClose: () => void;
}

export function ExpandableDrawer({ card, isOpen, onClose }: Props) {
    // Lock body scroll when drawer is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'unset';
        }
        return () => { document.body.style.overflow = 'unset'; };
    }, [isOpen]);

    if (!isOpen || !card) return null;

    return (
        <>
            <div className="drawer-overlay" onClick={onClose} />
            <div className="drawer-panel">
                <div className="drawer-header">
                    <div className="drawer-title">
                        <h2>{card.article}</h2>
                        <div className="drawer-subtitle">
                            Page {card.page} • Réglementation BCT
                        </div>
                    </div>
                    <button className="drawer-close" onClick={onClose}>
                        <X size={24} />
                    </button>
                </div>

                <div className="drawer-content">
                    <div className="drawer-section">
                        <h3>Extrait Pertinent</h3>
                        <div className="full-text-box">
                            {card.excerpt}
                        </div>
                    </div>

                    <div className="drawer-section">
                        <h3>Contexte Total</h3>
                        <p className="text-gray-400 text-sm mb-4">
                            Ce texte provient de l'analyse sémantique du document officiel.
                            Pour une analyse complète, veuillez consulter le document PDF original.
                        </p>
                        <div className="p-4 bg-slate-900 rounded border border-slate-700 text-slate-300 text-sm">
                            (Texte complet non disponible dans cette démo - seul l'extrait vectoriel est affiché)
                        </div>
                    </div>
                </div>

                <div className="disclaimer-text mt-4">
                    <div className="disclaimer-box">
                        <AlertCircle size={20} />
                        <span>
                            Support d'interprétation généré par IA – pas un conseil juridique officiel.
                            Toujours vérifier les circulaires officielles.
                        </span>
                    </div>
                </div>
            </div>
        </>
    );
}
