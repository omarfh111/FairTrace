"""
Expert Comptable Chatbot - Interactive financial advisor with RAG integration.
Only answers financial and credit-related questions.
"""

import json
import os
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from . import rag_retriever

os.environ.setdefault("LANGCHAIN_TRACING_V2", os.getenv("LANGCHAIN_TRACING_V2", "false"))


def get_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.4,
        api_key=OPENAI_API_KEY
    )


EXPERT_COMPTABLE_SYSTEM_PROMPT = """Tu es un Expert Comptable virtuel spécialisé dans l'analyse financière et le conseil en crédit.

⚠️ RÈGLE IMPORTANTE: Tu ne dois répondre QU'aux questions liées à:
- Finance personnelle et d'entreprise
- Crédit et prêts
- Comptabilité et fiscalité
- Ratios financiers et métriques
- Gestion de trésorerie
- Investissements et épargne
- Dettes et remboursements
- Budgétisation

Si quelqu'un pose une question hors de ces sujets (météo, sport, cuisine, politique, etc.), tu dois POLIMENT refuser et rediriger vers des questions financières.

Exemple de refus: "Je suis un expert comptable spécialisé en finance et crédit. Je ne peux pas répondre à cette question, mais je serais ravi de vous aider avec vos questions financières ! Par exemple, je peux vous expliquer comment améliorer votre ratio dette/revenu ou calculer votre capacité d'emprunt."

Tu as accès au profil financier du demandeur si disponible.

Tu dois être:
- Professionnel mais accessible
- Pédagogue et patient
- Précis dans tes explications
- Encourageant tout en restant honnête
- STRICT sur le périmètre des questions

Réponds toujours en français et de manière concise mais complète."""


# Keywords to detect financial questions
FINANCIAL_KEYWORDS = [
    'crédit', 'credit', 'prêt', 'pret', 'emprunt', 'dette', 'revenu', 'salaire',
    'ratio', 'taux', 'intérêt', 'interet', 'remboursement', 'mensualité', 'mensualite',
    'banque', 'financ', 'budget', 'épargne', 'epargne', 'investiss', 'comptab',
    'fiscal', 'impôt', 'impot', 'TVA', 'bilan', 'trésorerie', 'tresorerie',
    'capital', 'fonds', 'cash', 'liquidi', 'solvab', 'rentab', 'marge',
    'chiffre d\'affaires', 'CA', 'BFR', 'ROI', 'ROE', 'EBITDA', 'amortiss',
    'actif', 'passif', 'charges', 'produits', 'résultat', 'resultat',
    'startup', 'entreprise', 'société', 'societe', 'business', 'commer',
    'ARR', 'MRR', 'burn', 'runway', 'valorisation', 'levée', 'levee',
    'altman', 'score', 'notation', 'risque', 'défaut', 'defaut', 'faillite',
    'améliorer', 'ameliorer', 'optimiser', 'réduire', 'reduire', 'augmenter',
    'paiement', 'facture', 'client', 'fournisseur', 'stock', 'inventaire'
]


def is_financial_question(question: str) -> bool:
    """Check if the question is related to finance."""
    question_lower = question.lower()
    
    # Check for financial keywords
    for keyword in FINANCIAL_KEYWORDS:
        if keyword in question_lower:
            return True
    
    # Check for numbers with currency symbols (likely financial)
    if any(c in question for c in ['€', '$', '%']):
        return True
    
    return False


class ExpertComptableChatbot:
    """Interactive chatbot for financial advice - only answers financial questions."""
    
    def __init__(self, application: dict = None, application_type: str = None, decision: dict = None):
        self.application = application or {}
        self.application_type = application_type or "client"
        self.decision = decision
        self.conversation_history: List[Dict] = []
        self.llm = get_llm()
        self.similar_cases = []
        
        if application:
            try:
                self.similar_cases = rag_retriever.retrieve_similar_cases(
                    application_type=self.application_type,
                    application_data=self.application,
                    top_k=5
                )
            except Exception:
                self.similar_cases = []
    
    def _build_context(self) -> str:
        """Build context string from application and decision."""
        context = ""
        
        if self.application:
            context += f"\n=== PROFIL DU CLIENT ({self.application_type.upper()}) ===\n"
            
            if self.application_type == "client":
                context += f"""
- Revenu annuel: €{self.application.get('income_annual', 0):,.0f}
- Ratio dette/revenu: {self.application.get('debt_to_income_ratio', 0)*100:.1f}%
- Paiements manqués: {self.application.get('missed_payments_last_12m', 0)}
- Ancienneté emploi: {self.application.get('job_tenure_years', 0)} ans
- Type contrat: {self.application.get('contract_type', 'Non spécifié')}
"""
            elif self.application_type == "startup":
                context += f"""
- Secteur: {self.application.get('sector', 'Non spécifié')}
- ARR actuel: ${self.application.get('arr_current', 0):,.0f}
- Runway: {self.application.get('runway_months', 0):.1f} mois
- Burn multiple: {self.application.get('burn_multiple', 0):.2f}
"""
            else:
                context += f"""
- Industrie: {self.application.get('industry_code', 'Non spécifié')}
- Revenu annuel: €{self.application.get('revenue_annual', 0):,.0f}
- Score Altman Z: {self.application.get('altman_z_score', 0):.2f}
- Current ratio: {self.application.get('current_ratio', 0):.2f}
"""
        
        if self.decision:
            context += f"""
=== ANALYSE DE CRÉDIT ===
- Décision: {self.decision.get('decision', 'N/A')}
- Niveau de risque: {self.decision.get('overall_risk_level', 'N/A')}
"""
        
        return context
    
    def chat(self, user_message: str) -> str:
        """
        Send a message and get a response.
        Only answers financial questions.
        """
        # Check if question is financial
        if not is_financial_question(user_message):
            # Check with LLM if it's a greeting or follow-up
            is_greeting = any(g in user_message.lower() for g in ['bonjour', 'salut', 'hello', 'merci', 'au revoir'])
            
            if is_greeting:
                self.conversation_history.append({"role": "user", "content": user_message})
                response = "Bonjour ! Je suis votre expert comptable virtuel. Je suis spécialisé dans les questions de finance, crédit et comptabilité. Comment puis-je vous aider avec vos finances aujourd'hui ?"
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            
            # Not a financial question - politely refuse
            self.conversation_history.append({"role": "user", "content": user_message})
            response = """🚫 **Question hors périmètre**

Je suis un expert comptable spécialisé en **finance, crédit et comptabilité**. Je ne suis pas en mesure de répondre à cette question.

Mais je serais ravi de vous aider avec des questions comme:
- 💰 Comment améliorer mon ratio dette/revenu ?
- 📊 Quel est un bon score de crédit ?
- 🏦 Comment calculer ma capacité d'emprunt ?
- 📈 Comment optimiser ma trésorerie ?

Quelle question financière puis-je clarifier pour vous ?"""
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # Build messages for financial question
        context = self._build_context()
        
        system_message = EXPERT_COMPTABLE_SYSTEM_PROMPT
        if context:
            system_message += f"\n\nContexte du client:\n{context}"
        
        messages = [SystemMessage(content=system_message)]
        
        # Add conversation history (last 10 messages)
        for msg in self.conversation_history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=user_message))
        
        # Get response
        response = self.llm.invoke(
            messages,
            config={"run_name": "Expert Comptable Chat", "tags": ["chatbot", "expert_comptable"]}
        )
        
        # Save to history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response.content})
        
        return response.content
    
    def get_suggested_questions(self) -> List[str]:
        """Get suggested questions based on the context."""
        if self.application_type == "client":
            return [
                "Comment réduire mon ratio dette/revenu ?",
                "Quel impact des paiements manqués sur mon crédit ?",
                "Comment améliorer mon score de crédit ?",
                "Quelle utilisation de crédit est saine ?"
            ]
        elif self.application_type == "startup":
            return [
                "Comment améliorer mon burn multiple ?",
                "Quel runway est suffisant ?",
                "Comment optimiser mon ratio CAC/LTV ?",
                "Quelles métriques comptent pour les prêteurs ?"
            ]
        else:
            return [
                "Qu'est-ce que le score Altman Z ?",
                "Comment améliorer mon current ratio ?",
                "Comment réduire mon ratio dette/capitaux ?",
                "Comment améliorer ma couverture d'intérêts ?"
            ]
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def update_context(self, application: dict = None, decision: dict = None):
        """Update the chatbot context."""
        if application:
            self.application = application
        if decision:
            self.decision = decision
