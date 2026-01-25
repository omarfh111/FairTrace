export type ApplicationType = 'startup' | 'client' | 'enterprise';

// Client Application (individual borrowers) - matches generate_data.py
export interface ClientApplication {
  type: 'client';
  // Personal
  age: number;
  contract_type: 'CDI' | 'CDD' | 'Freelance' | 'Unemployed';
  job_tenure_years: number;
  // Financial
  income_annual: number;
  debt_to_income_ratio: number;
  savings_rate: number;
  spending_volatility_index: number;
  // Credit
  missed_payments_last_12m: number;
  credit_utilization_avg: number;
  loan_purpose: string;
}

// Startup Application - matches generate_data.py
export interface StartupApplication {
  type: 'startup';
  sector: string;
  founder_experience_years: number;
  vc_backing: boolean;
  // Revenue
  arr_current: number;
  arr_growth_yoy: number;
  // Burn & Runway
  burn_rate_monthly: number;
  runway_months: number;
  // Unit Economics
  cac_ltv_ratio: number;
  churn_rate_monthly: number;
  burn_multiple: number;
}

// Enterprise Application - matches generate_data.py
export interface EnterpriseApplication {
  type: 'enterprise';
  industry_code: string;
  // Financials
  revenue_annual: number;
  net_profit_margin: number;
  // Ratios
  current_ratio: number;
  quick_ratio: number;
  debt_to_equity: number;
  interest_coverage_ratio: number;
  // Risk indicators
  altman_z_score: number;
  esg_risk_score: number;
  legal_lawsuits_active: number;
}

export type Application = ClientApplication | StartupApplication | EnterpriseApplication;

export type Decision = 'APPROVE' | 'REJECT' | 'CONDITIONAL' | 'ESCALATE';
export type Recommendation = 'APPROVE' | 'REJECT' | 'CONDITIONAL' | 'CAUTION';

export interface SimilarCase {
  entityId: string;
  outcome: 'APPROVED' | 'BANKRUPT' | 'REJECTED' | 'DEFAULTED' | 'FUNDED' | 'STABLE' | 'WATCHLIST' | 'DEFAULT';
  similarity: number;
  reasoning: string;
}

export interface AgentVerdict {
  agentName: string;
  agentRole: string;
  agentColor: 'risk' | 'fairness' | 'trajectory';
  recommendation: Recommendation;
  reasoning: string;
  concerns: string[];
  mitigatingFactors: string[];
  similarCases: SimilarCase[];
  confidence: number;
}

export interface DecisionResult {
  decision: Decision;
  confidence: number;
  processingTime: number;
  agents: AgentVerdict[];
  summary: string;
  applicationId: string;
}
