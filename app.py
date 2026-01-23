"""
Credit Decision Memory - Streamlit Web Interface
Enhanced with PDF Reports, Advisor Agent, and Expert Comptable Chatbot

Run with: streamlit run app.py
"""

import os
import streamlit as st
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set LangSmith tracing environment variables BEFORE importing agents
if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "").strip().strip('"')
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "fairtrace")

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import evaluate_credit_application
from agents.config import validate_config, LLM_MODEL
from agents.schemas import FinalDecision, RiskLevel, DecisionOutcome
from agents.pdf_generator import generate_pdf_report
from agents.advisor_agent import generate_advice
from agents.expert_chatbot import ExpertComptableChatbot

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Credit Decision Memory",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "decision" not in st.session_state:
    st.session_state.decision = None
if "application" not in st.session_state:
    st.session_state.application = None
if "app_type" not in st.session_state:
    st.session_state.app_type = None
if "chatbot" not in st.session_state:
    st.session_state.chatbot = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "advice" not in st.session_state:
    st.session_state.advice = None

# =============================================================================
# CUSTOM CSS
# =============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .decision-approved {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    .decision-rejected {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    .decision-review {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    .tab-content {
        padding: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# HEADER
# =============================================================================
st.markdown('<h1 class="main-header">🏦 Credit Decision Memory</h1>', unsafe_allow_html=True)

# =============================================================================
# TABS
# =============================================================================
tab1, tab2, tab3 = st.tabs(["📊 Analyse de Crédit", "💡 Conseils d'Amélioration", "💬 Expert Comptable"])

# =============================================================================
# TAB 1: CREDIT ANALYSIS
# =============================================================================
with tab1:
    col_form, col_result = st.columns([1, 2])
    
    with col_form:
        st.subheader("📋 Nouvelle Demande")
        
        app_type = st.selectbox(
            "Type de demandeur",
            ["client", "startup", "enterprise"],
            format_func=lambda x: {"client": "👤 Client", "startup": "🚀 Startup", "enterprise": "🏢 Entreprise"}[x]
        )
        
        # Dynamic form based on application type
        if app_type == "client":
            income = st.number_input("Revenu annuel (€)", min_value=0, value=45000, step=1000)
            dti = st.slider("Ratio dette/revenu", 0.0, 1.0, 0.25, 0.05)
            missed = st.number_input("Paiements manqués (12 mois)", min_value=0, max_value=12, value=0)
            tenure = st.number_input("Ancienneté emploi (années)", min_value=0.0, value=3.0, step=0.5)
            contract = st.selectbox("Type de contrat", ["CDI", "CDD", "Freelance", "Interim"])
            purpose = st.selectbox("Objectif du prêt", ["Home Improvement", "Education", "Vehicle", "Debt Consolidation", "Business"])
            credit_util = st.slider("Utilisation crédit moyenne", 0.0, 1.0, 0.3, 0.05)
            history = st.text_area("Historique de crédit", "Bon historique de crédit avec remboursements réguliers.")
            
            application = {
                "income_annual": income,
                "debt_to_income_ratio": dti,
                "missed_payments_last_12m": missed,
                "job_tenure_years": tenure,
                "age": 35,
                "contract_type": contract,
                "loan_purpose": purpose,
                "credit_utilization_avg": credit_util,
                "credit_history": history
            }
        
        elif app_type == "startup":
            sector = st.selectbox("Secteur", ["FinTech", "HealthTech", "EdTech", "E-commerce", "SaaS", "AI/ML"])
            founder_exp = st.number_input("Expérience fondateur (années)", min_value=0, value=5)
            vc_backing = st.checkbox("Financé par VC")
            arr = st.number_input("ARR actuel ($)", min_value=0, value=1000000, step=100000)
            arr_growth = st.slider("Croissance ARR YoY", -0.5, 3.0, 0.5, 0.1)
            burn = st.number_input("Burn rate mensuel ($)", min_value=0, value=80000, step=10000)
            runway = st.number_input("Runway (mois)", min_value=0.0, value=12.0, step=1.0)
            burn_multiple = st.number_input("Burn Multiple", min_value=0.0, value=1.0, step=0.1)
            pitch = st.text_area("Pitch", "Startup innovante dans le secteur...")
            
            application = {
                "sector": sector,
                "founder_experience_years": founder_exp,
                "vc_backing": vc_backing,
                "arr_current": arr,
                "arr_growth_yoy": arr_growth,
                "burn_rate_monthly": burn,
                "runway_months": runway,
                "cac_ltv_ratio": 0.3,
                "churn_rate_monthly": 0.03,
                "burn_multiple": burn_multiple,
                "pitch_narrative": pitch
            }
        
        else:  # enterprise
            industry = st.selectbox("Industrie", ["Manufacturing", "Technology", "Healthcare", "Retail", "Finance", "Energy"])
            revenue = st.number_input("Revenu annuel (€)", min_value=0, value=10000000, step=1000000)
            margin = st.slider("Marge nette", -0.5, 0.5, 0.08, 0.01)
            current_ratio = st.number_input("Current Ratio", min_value=0.0, value=1.5, step=0.1)
            quick_ratio = st.number_input("Quick Ratio", min_value=0.0, value=1.2, step=0.1)
            dte = st.number_input("Debt-to-Equity", min_value=0.0, value=0.5, step=0.1)
            interest_cov = st.number_input("Interest Coverage Ratio", min_value=0.0, value=3.0, step=0.5)
            altman = st.number_input("Altman Z-Score", min_value=0.0, value=2.5, step=0.1)
            esg = st.slider("ESG Risk Score", 0, 100, 40)
            lawsuits = st.number_input("Procès actifs", min_value=0, value=0)
            risk_section = st.text_area("Section Risques", "Risques principaux identifiés...")
            
            application = {
                "industry_code": industry,
                "revenue_annual": revenue,
                "net_profit_margin": margin,
                "current_ratio": current_ratio,
                "quick_ratio": quick_ratio,
                "debt_to_equity": dte,
                "interest_coverage_ratio": interest_cov,
                "altman_z_score": altman,
                "esg_risk_score": esg,
                "legal_lawsuits_active": lawsuits,
                "ceo_name": "CEO",
                "ceo_experience_years": 15,
                "ceo_track_record": "Expérience positive",
                "annual_report_risk_section": risk_section
            }
        
        analyze_button = st.button("🔍 Analyser la Demande", type="primary", use_container_width=True)
    
    with col_result:
        if analyze_button:
            try:
                validate_config()
            except ValueError as e:
                st.error(f"❌ Erreur de configuration: {e}")
                st.stop()
            
            with st.spinner("🔄 Analyse en cours par les 5 agents IA..."):
                try:
                    decision = evaluate_credit_application(application, app_type)
                    st.session_state.decision = decision
                    st.session_state.application = application
                    st.session_state.app_type = app_type
                    st.session_state.advice = None  # Reset advice
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'analyse: {e}")
                    st.stop()
        
        # Display results if available
        if st.session_state.decision:
            decision = st.session_state.decision
            
            # Decision Banner
            decision_class = {
                DecisionOutcome.APPROVED: "decision-approved",
                DecisionOutcome.REJECTED: "decision-rejected",
                DecisionOutcome.REVIEW_NEEDED: "decision-review"
            }
            decision_icon = {
                DecisionOutcome.APPROVED: "✅",
                DecisionOutcome.REJECTED: "❌",
                DecisionOutcome.REVIEW_NEEDED: "⚠️"
            }
            
            st.markdown(f'''
            <div class="{decision_class[decision.decision]}">
                {decision_icon[decision.decision]} DÉCISION: {decision.decision.value}
            </div>
            ''', unsafe_allow_html=True)
            
            # Key Metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Confiance", f"{decision.confidence*100:.0f}%")
            with col2:
                risk_colors = {RiskLevel.LOW: "🟢", RiskLevel.MEDIUM: "🟡", RiskLevel.HIGH: "🟠", RiskLevel.CRITICAL: "🔴"}
                st.metric("Risque", f"{risk_colors[decision.overall_risk_level]} {decision.overall_risk_level.value}")
            with col3:
                processing_time = decision.processing_time_seconds or 0
                st.metric("Temps", f"{processing_time:.1f}s")
            with col4:
                st.metric("Coût", "$0.002")
            with col5:
                st.metric("Agents", "5")
            
            # Executive Summary
            st.subheader("📝 Résumé Exécutif")
            st.info(decision.executive_summary)
            
            # Key Reasons
            st.subheader("🎯 Raisons Principales")
            for i, reason in enumerate(decision.key_reasons, 1):
                st.markdown(f"**{i}.** {reason}")
            
            # Agent Analyses
            with st.expander("🤖 Détails des Agents", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    if decision.financial_analysis:
                        fa = decision.financial_analysis
                        st.markdown(f"**💰 Financial Agent** - {fa.risk_level.value}")
                        st.progress(fa.confidence)
                        st.markdown(f"_{fa.recommendation}_")
                    
                    if decision.narrative_analysis:
                        na = decision.narrative_analysis
                        st.markdown(f"**📝 Narrative Agent** - {na.risk_level.value}")
                        st.progress(na.confidence)
                
                with col2:
                    if decision.risk_analysis:
                        ra = decision.risk_analysis
                        st.markdown(f"**⚠️ Risk Agent** - {ra.risk_level.value}")
                        if ra.red_flags:
                            for flag in ra.red_flags[:3]:
                                st.markdown(f"🚨 {flag}")
                    
                    if decision.prediction_result:
                        pr = decision.prediction_result
                        st.markdown(f"**🔮 Prediction Agent**")
                        st.metric("Prob. Défaut", f"{pr.default_probability*100:.0f}%")
            
            # Export Section
            st.divider()
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # PDF Export
                pdf_bytes = generate_pdf_report(decision, st.session_state.application, st.session_state.app_type)
                st.download_button(
                    "📄 Télécharger PDF",
                    pdf_bytes,
                    file_name=f"rapport_credit_{st.session_state.app_type}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col2:
                # JSON Export
                st.download_button(
                    "📋 Exporter JSON",
                    json.dumps(decision.model_dump(), indent=2, default=str),
                    file_name="credit_decision.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col3:
                if st.button("💡 Obtenir Conseils", use_container_width=True):
                    with st.spinner("Génération des conseils..."):
                        st.session_state.advice = generate_advice(decision, st.session_state.application, st.session_state.app_type)
        else:
            st.markdown("""
            ### 👋 Bienvenue!
            
            Remplissez le formulaire à gauche et cliquez sur **Analyser** pour obtenir:
            - 🤖 Analyse par 5 agents IA spécialisés
            - 📊 Décision expliquée avec cas similaires
            - 📄 Rapport PDF professionnel
            - 💡 Conseils pour améliorer votre profil
            - 💬 Chat avec un Expert Comptable IA
            """)

# =============================================================================
# TAB 2: ADVICE
# =============================================================================
with tab2:
    st.subheader("💡 Conseils pour Améliorer Votre Profil de Crédit")
    
    if st.session_state.decision is None:
        st.warning("⚠️ Effectuez d'abord une analyse dans l'onglet 'Analyse de Crédit'")
    else:
        if st.session_state.advice is None:
            if st.button("🎯 Générer les Conseils Personnalisés", type="primary"):
                with st.spinner("L'agent conseiller analyse votre profil..."):
                    st.session_state.advice = generate_advice(
                        st.session_state.decision,
                        st.session_state.application,
                        st.session_state.app_type
                    )
        
        if st.session_state.advice:
            advice = st.session_state.advice
            
            # Overall Assessment
            st.markdown(f"### 📊 Évaluation Globale")
            st.info(advice.get('overall_assessment', 'N/A'))
            
            # Main Weaknesses
            if advice.get('main_weaknesses'):
                st.markdown("### ⚠️ Points Faibles Identifiés")
                for weakness in advice['main_weaknesses']:
                    st.markdown(f"- {weakness}")
            
            # Quick Wins
            if advice.get('quick_wins'):
                st.markdown("### ⚡ Actions Rapides (Quick Wins)")
                for win in advice['quick_wins']:
                    st.success(f"✓ {win}")
            
            # Detailed Recommendations
            if advice.get('recommendations'):
                st.markdown("### 📋 Plan d'Action Détaillé")
                for i, rec in enumerate(advice['recommendations'], 1):
                    priority = rec.get('priority', 'MEDIUM')
                    priority_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(priority, "⚪")
                    
                    with st.expander(f"{priority_color} {rec.get('action', 'Action')}", expanded=(i <= 2)):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Impact:** {rec.get('impact', 'N/A')}")
                        with col2:
                            st.markdown(f"**Durée:** {rec.get('timeline', 'N/A')}")
                        if rec.get('details'):
                            st.markdown(f"**Détails:** {rec['details']}")
            
            # Long Term Strategy
            if advice.get('long_term_strategy'):
                st.markdown("### 🎯 Stratégie Long Terme")
                st.info(advice['long_term_strategy'])
            
            # Estimated Improvement
            if advice.get('estimated_improvement'):
                st.markdown("### 📈 Amélioration Estimée")
                st.success(advice['estimated_improvement'])

# =============================================================================
# TAB 3: EXPERT CHATBOT
# =============================================================================
with tab3:
    st.subheader("💬 Expert Comptable IA")
    st.markdown("Posez vos questions financières à notre expert comptable virtuel.")
    
    # Initialize chatbot with context if available
    if st.session_state.chatbot is None:
        if st.session_state.application:
            st.session_state.chatbot = ExpertComptableChatbot(
                application=st.session_state.application,
                application_type=st.session_state.app_type,
                decision=st.session_state.decision.model_dump() if st.session_state.decision else None
            )
        else:
            st.session_state.chatbot = ExpertComptableChatbot()
    
    # Update chatbot context if new analysis
    if st.session_state.application and st.session_state.chatbot:
        st.session_state.chatbot.update_context(
            application=st.session_state.application,
            decision=st.session_state.decision.model_dump() if st.session_state.decision else None
        )
    
    # Suggested questions
    if not st.session_state.chat_messages:
        st.markdown("**💡 Questions suggérées:**")
        suggested = st.session_state.chatbot.get_suggested_questions() if st.session_state.chatbot else []
        cols = st.columns(2)
        for i, question in enumerate(suggested[:4]):
            with cols[i % 2]:
                if st.button(question, key=f"suggested_{i}"):
                    st.session_state.chat_messages.append({"role": "user", "content": question})
                    with st.spinner("L'expert réfléchit..."):
                        response = st.session_state.chatbot.chat(question)
                        st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    st.rerun()
    
    # Chat history
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])
    
    # Chat input
    user_input = st.chat_input("Posez votre question à l'expert comptable...")
    
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)
        
        with st.spinner("L'expert analyse votre question..."):
            response = st.session_state.chatbot.chat(user_input)
        
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)
    
    # Clear chat button
    if st.session_state.chat_messages:
        if st.button("🗑️ Effacer la conversation"):
            st.session_state.chat_messages = []
            if st.session_state.chatbot:
                st.session_state.chatbot.clear_history()
            st.rerun()

# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.markdown("""
<p style="text-align: center; color: #999; font-size: 0.8rem;">
    Credit Decision Memory | 6 Agents IA: Financial, Risk, Narrative, Prediction, Advisor, Expert Comptable | 
    Powered by Qdrant + LangGraph + OpenAI (gpt-4o-mini)
</p>
""", unsafe_allow_html=True)
