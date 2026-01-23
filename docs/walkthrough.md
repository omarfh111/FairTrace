# Credit Decision Memory v2 - Walkthrough

Guide complet du système multi-agents pour décisions de crédit.

## 🎯 Vue d'Ensemble

Ce système utilise **6 agents IA spécialisés** orchestrés par **LangGraph** pour analyser des demandes de crédit et fournir des décisions expliquables.

---

## 🤖 Les 6 Agents

| Agent | Rôle | Output |
|-------|------|--------|
| 💰 Financial | Analyse ratios financiers | Risk level + recommendations |
| ⚠️ Risk | Détection anomalies | Red flags + outliers |
| 📝 Narrative | Analyse textuelle | Signaux qualitatifs |
| 🔮 Prediction | Prédiction défaut | Probabilité + timeline |
| 💡 Advisor | Conseils amélioration | Plan d'action |
| 💬 Expert | Chatbot comptable | Réponses interactives |

---

## 📊 Flux de Travail

```
Demande de crédit
       │
       ▼
┌──────────────────┐
│  RAG Retriever   │ ← Recherche cas similaires dans Qdrant
└──────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│         Agents parallèles (LangGraph)         │
│  Financial → Risk → Narrative → Prediction   │
└──────────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│   Orchestrator   │ ← Synthèse + Décision finale
└──────────────────┘
       │
       ▼
    Résultat: APPROVED / REJECTED / REVIEW_NEEDED
```

---

## 🖥️ Interface Streamlit (3 Onglets)

### Onglet 1: 📊 Analyse de Crédit
- Formulaire de saisie (Client / Startup / Enterprise)
- Métriques: Confiance, Risque, Temps, Coût
- Résumé exécutif et raisons
- Export PDF et JSON

### Onglet 2: 💡 Conseils
- Points faibles identifiés
- Quick Wins (actions rapides)
- Plan d'action avec priorités
- Stratégie long terme

### Onglet 3: 💬 Expert Comptable
- Chat interactif avec l'IA
- Questions suggérées
- Ne répond qu'aux questions financières
- Historique de conversation

---

## 🚀 Lancer l'Application

```bash
# Activer l'environnement
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Lancer Streamlit
streamlit run app.py
```

**URL:** http://localhost:8501

---

## 📄 Génération PDF

Le rapport PDF inclut:
- ✅ Bannière de décision colorée (vert/rouge/orange)
- ✅ Métriques clés en tableau
- ✅ Résumé exécutif
- ✅ Raisons principales
- ✅ Analyses de chaque agent
- ✅ Red flags identifiés
- ✅ Conditions et prochaines étapes
- ✅ Cas similaires historiques

---

## 💰 Coûts OpenAI

| Opération | Coût Estimé |
|-----------|-------------|
| 1 analyse complète | ~$0.002 |
| Conseil Advisor | ~$0.0005 |
| Chat Expert | ~$0.0003/message |

**Modèle utilisé:** gpt-4o-mini (économique)

---

## ✅ Vérification

- ✓ 6 agents fonctionnels
- ✓ RAG avec Qdrant opérationnel
- ✓ PDF Generator créé
- ✓ Advisor Agent créé
- ✓ Expert Chatbot créé (limité aux questions financières)
- ✓ Interface Streamlit avec 3 onglets
- ✓ Gestion d'erreurs JSON robuste
