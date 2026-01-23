"""
PDF Report Generator - Creates professional credit analysis reports.
"""

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from .schemas import FinalDecision, RiskLevel, DecisionOutcome


def get_risk_color(risk_level: RiskLevel):
    """Get color for risk level."""
    colors_map = {
        RiskLevel.LOW: colors.HexColor('#11998e'),
        RiskLevel.MEDIUM: colors.HexColor('#f5a623'),
        RiskLevel.HIGH: colors.HexColor('#eb3349'),
        RiskLevel.CRITICAL: colors.HexColor('#8b0000'),
    }
    return colors_map.get(risk_level, colors.black)


def get_decision_color(decision: DecisionOutcome):
    """Get color for decision."""
    colors_map = {
        DecisionOutcome.APPROVED: colors.HexColor('#11998e'),
        DecisionOutcome.REJECTED: colors.HexColor('#eb3349'),
        DecisionOutcome.REVIEW_NEEDED: colors.HexColor('#f5a623'),
    }
    return colors_map.get(decision, colors.black)


def generate_pdf_report(decision: FinalDecision, application: dict, application_type: str) -> bytes:
    """
    Generate a PDF report for the credit decision.
    
    Returns:
        PDF content as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceBefore=20,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#444444'),
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )
    
    # Build content
    content = []
    
    # Title
    content.append(Paragraph("🏦 Credit Decision Memory", title_style))
    content.append(Paragraph("Rapport d'Analyse de Crédit", styles['Heading2']))
    content.append(Spacer(1, 20))
    
    # Date and type
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    type_labels = {"client": "Client (Particulier)", "startup": "Startup", "enterprise": "Entreprise"}
    content.append(Paragraph(f"<b>Date:</b> {date_str}", body_style))
    content.append(Paragraph(f"<b>Type de demandeur:</b> {type_labels.get(application_type, application_type)}", body_style))
    content.append(Spacer(1, 20))
    
    # Decision Box
    decision_text = f"DÉCISION: {decision.decision.value}"
    decision_color = get_decision_color(decision.decision)
    
    decision_style = ParagraphStyle(
        'Decision',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.white,
        alignment=TA_CENTER,
        backColor=decision_color,
        borderPadding=10
    )
    
    decision_table = Table([[Paragraph(decision_text, decision_style)]], colWidths=[16*cm])
    decision_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), decision_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 18),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))
    content.append(decision_table)
    content.append(Spacer(1, 20))
    
    # Key Metrics
    content.append(Paragraph("📊 Métriques Clés", heading_style))
    
    metrics_data = [
        ["Confiance", "Niveau de Risque", "Temps d'Analyse"],
        [f"{decision.confidence*100:.0f}%", decision.overall_risk_level.value, f"{decision.processing_time_seconds or 0:.2f}s"]
    ]
    
    metrics_table = Table(metrics_data, colWidths=[5*cm, 5*cm, 5*cm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
    ]))
    content.append(metrics_table)
    content.append(Spacer(1, 20))
    
    # Executive Summary
    content.append(Paragraph("📝 Résumé Exécutif", heading_style))
    content.append(Paragraph(decision.executive_summary or "Non disponible", body_style))
    content.append(Spacer(1, 15))
    
    # Key Reasons
    content.append(Paragraph("🎯 Raisons Principales", heading_style))
    for i, reason in enumerate(decision.key_reasons or [], 1):
        content.append(Paragraph(f"<b>{i}.</b> {reason}", body_style))
    content.append(Spacer(1, 15))
    
    # Agent Analyses
    content.append(Paragraph("🤖 Analyses des Agents", heading_style))
    
    agents_data = [["Agent", "Niveau de Risque", "Confiance", "Recommandation"]]
    
    if decision.financial_analysis:
        fa = decision.financial_analysis
        agents_data.append([
            "💰 Financial Agent",
            fa.risk_level.value,
            f"{fa.confidence*100:.0f}%",
            fa.recommendation[:50] + "..." if len(fa.recommendation) > 50 else fa.recommendation
        ])
    
    if decision.risk_analysis:
        ra = decision.risk_analysis
        agents_data.append([
            "⚠️ Risk Agent",
            ra.risk_level.value,
            f"{ra.confidence*100:.0f}%",
            ra.recommendation[:50] + "..." if len(ra.recommendation) > 50 else ra.recommendation
        ])
    
    if decision.narrative_analysis:
        na = decision.narrative_analysis
        agents_data.append([
            "📝 Narrative Agent",
            na.risk_level.value,
            f"{na.confidence*100:.0f}%",
            na.recommendation[:50] + "..." if len(na.recommendation) > 50 else na.recommendation
        ])
    
    if decision.prediction_result:
        pr = decision.prediction_result
        agents_data.append([
            "🔮 Prediction Agent",
            f"{pr.default_probability*100:.0f}% défaut",
            pr.time_to_risk or "N/A",
            pr.risk_trajectory
        ])
    
    if len(agents_data) > 1:
        agents_table = Table(agents_data, colWidths=[4*cm, 3*cm, 2.5*cm, 6*cm])
        agents_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        content.append(agents_table)
    content.append(Spacer(1, 15))
    
    # Red Flags
    all_red_flags = []
    if decision.financial_analysis and decision.financial_analysis.red_flags:
        all_red_flags.extend(decision.financial_analysis.red_flags)
    if decision.risk_analysis and decision.risk_analysis.red_flags:
        all_red_flags.extend(decision.risk_analysis.red_flags)
    
    if all_red_flags:
        content.append(Paragraph("🚨 Points d'Attention", heading_style))
        for flag in all_red_flags[:5]:
            content.append(Paragraph(f"• {flag}", body_style))
        content.append(Spacer(1, 15))
    
    # Conditions
    if decision.conditions:
        content.append(Paragraph("📋 Conditions", heading_style))
        for condition in decision.conditions:
            content.append(Paragraph(f"✓ {condition}", body_style))
        content.append(Spacer(1, 15))
    
    # Next Steps
    if decision.next_steps:
        content.append(Paragraph("➡️ Prochaines Étapes", heading_style))
        for step in decision.next_steps:
            content.append(Paragraph(f"→ {step}", body_style))
        content.append(Spacer(1, 15))
    
    # Similar Cases
    if decision.similar_precedents:
        content.append(Paragraph("📚 Cas Similaires Historiques", heading_style))
        cases_data = [["ID", "Outcome", "Similarité"]]
        for case in decision.similar_precedents[:5]:
            cases_data.append([case.case_id, case.outcome, f"{case.similarity_score:.2f}"])
        
        cases_table = Table(cases_data, colWidths=[5*cm, 5*cm, 5*cm])
        cases_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6c757d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ]))
        content.append(cases_table)
    
    # Footer
    content.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER
    )
    content.append(Paragraph("─" * 60, footer_style))
    content.append(Paragraph("Credit Decision Memory | Powered by Multi-Agent AI System", footer_style))
    content.append(Paragraph("Ce rapport est généré automatiquement à des fins d'aide à la décision.", footer_style))
    
    # Build PDF
    doc.build(content)
    
    return buffer.getvalue()
