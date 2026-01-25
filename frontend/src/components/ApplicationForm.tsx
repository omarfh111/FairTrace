import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/ui/GlassCard";
import { FloatingInput } from "@/components/ui/FloatingInput";
import { GradientButton } from "@/components/ui/GradientButton";
import { Application, ApplicationType } from "@/types/application";
import { Rocket, User, Building2 } from "lucide-react";

interface ApplicationFormProps {
  onSubmit: (application: Application) => void;
  isLoading: boolean;
}

const tabs: { id: ApplicationType; label: string; icon: React.ReactNode }[] = [
  { id: 'startup', label: 'Startup', icon: <Rocket className="w-4 h-4" /> },
  { id: 'client', label: 'Client', icon: <User className="w-4 h-4" /> },
  { id: 'enterprise', label: 'Enterprise', icon: <Building2 className="w-4 h-4" /> },
];

// Test examples matching generate_data.py structure
const clientExample = {
  age: '35',
  contract_type: 'CDI',
  job_tenure_years: '8',
  income_annual: '52000',
  debt_to_income_ratio: '0.38',
  savings_rate: '0.15',
  spending_volatility_index: '0.25',
  missed_payments_last_12m: '1',
  credit_utilization_avg: '0.45',
  loan_purpose: 'Home renovation',
};

export const ApplicationForm = ({ onSubmit, isLoading }: ApplicationFormProps) => {
  const [activeTab, setActiveTab] = useState<ApplicationType>('client');

  // Client form state (matches generate_data.py)
  const [clientForm, setClientForm] = useState({
    age: '',
    contract_type: 'CDI',
    job_tenure_years: '',
    income_annual: '',
    debt_to_income_ratio: '',
    savings_rate: '',
    spending_volatility_index: '',
    missed_payments_last_12m: '',
    credit_utilization_avg: '',
    loan_purpose: 'Home renovation',
  });

  // Startup form state (matches generate_data.py)
  const [startupForm, setStartupForm] = useState({
    sector: 'SaaS',
    founder_experience_years: '',
    vc_backing: false,
    arr_current: '',
    arr_growth_yoy: '',
    burn_rate_monthly: '',
    runway_months: '',
    cac_ltv_ratio: '',
    churn_rate_monthly: '',
    burn_multiple: '',
  });

  // Enterprise form state (matches generate_data.py)
  const [enterpriseForm, setEnterpriseForm] = useState({
    industry_code: 'Technology',
    revenue_annual: '',
    net_profit_margin: '',
    current_ratio: '',
    quick_ratio: '',
    debt_to_equity: '',
    interest_coverage_ratio: '',
    altman_z_score: '',
    esg_risk_score: '',
    legal_lawsuits_active: '',
  });

  const loadClientExample = () => {
    setClientForm(clientExample);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    let application: Application;

    if (activeTab === 'client') {
      application = {
        type: 'client',
        age: parseInt(clientForm.age) || 0,
        contract_type: clientForm.contract_type as any,
        job_tenure_years: parseInt(clientForm.job_tenure_years) || 0,
        income_annual: parseFloat(clientForm.income_annual) || 0,
        debt_to_income_ratio: parseFloat(clientForm.debt_to_income_ratio) || 0,
        savings_rate: parseFloat(clientForm.savings_rate) || 0,
        spending_volatility_index: parseFloat(clientForm.spending_volatility_index) || 0,
        missed_payments_last_12m: parseInt(clientForm.missed_payments_last_12m) || 0,
        credit_utilization_avg: parseFloat(clientForm.credit_utilization_avg) || 0,
        loan_purpose: clientForm.loan_purpose,
      };
    } else if (activeTab === 'startup') {
      application = {
        type: 'startup',
        sector: startupForm.sector,
        founder_experience_years: parseInt(startupForm.founder_experience_years) || 0,
        vc_backing: startupForm.vc_backing,
        arr_current: parseFloat(startupForm.arr_current) || 0,
        arr_growth_yoy: parseFloat(startupForm.arr_growth_yoy) || 0,
        burn_rate_monthly: parseFloat(startupForm.burn_rate_monthly) || 0,
        runway_months: parseFloat(startupForm.runway_months) || 0,
        cac_ltv_ratio: parseFloat(startupForm.cac_ltv_ratio) || 0,
        churn_rate_monthly: parseFloat(startupForm.churn_rate_monthly) || 0,
        burn_multiple: parseFloat(startupForm.burn_multiple) || 0,
      };
    } else {
      application = {
        type: 'enterprise',
        industry_code: enterpriseForm.industry_code,
        revenue_annual: parseFloat(enterpriseForm.revenue_annual) || 0,
        net_profit_margin: parseFloat(enterpriseForm.net_profit_margin) || 0,
        current_ratio: parseFloat(enterpriseForm.current_ratio) || 0,
        quick_ratio: parseFloat(enterpriseForm.quick_ratio) || 0,
        debt_to_equity: parseFloat(enterpriseForm.debt_to_equity) || 0,
        interest_coverage_ratio: parseFloat(enterpriseForm.interest_coverage_ratio) || 0,
        altman_z_score: parseFloat(enterpriseForm.altman_z_score) || 0,
        esg_risk_score: parseFloat(enterpriseForm.esg_risk_score) || 0,
        legal_lawsuits_active: parseInt(enterpriseForm.legal_lawsuits_active) || 0,
      };
    }

    onSubmit(application);
  };

  return (
    <GlassCard className="p-6 md:p-8" hover={false}>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold mb-2">New Application</h2>
          <p className="text-muted-foreground text-sm">Submit a credit application for multi-agent analysis</p>
        </div>
        {activeTab === 'client' && (
          <button
            type="button"
            onClick={loadClientExample}
            className="text-xs px-3 py-1.5 bg-primary/20 text-primary rounded-lg hover:bg-primary/30 transition-colors"
          >
            Load Example
          </button>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 p-1 bg-secondary/50 rounded-lg mb-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium transition-all duration-200",
              activeTab === tab.id
                ? "bg-primary text-primary-foreground shadow-lg"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary"
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        <AnimatePresence mode="wait">
          {/* CLIENT FORM */}
          {activeTab === 'client' && (
            <motion.div
              key="client"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {/* Personal */}
              <div className="text-xs text-muted-foreground font-medium mb-2">Personal Information</div>
              <div className="grid grid-cols-3 gap-4">
                <FloatingInput
                  label="Age"
                  type="number"
                  value={clientForm.age}
                  onChange={(e) => setClientForm({ ...clientForm, age: e.target.value })}
                  required
                />
                <div className="relative">
                  <select
                    value={clientForm.contract_type}
                    onChange={(e) => setClientForm({ ...clientForm, contract_type: e.target.value })}
                    className="w-full px-4 py-3 bg-secondary/50 border border-glass-border rounded-lg text-foreground focus:outline-none focus:border-primary appearance-none"
                  >
                    <option value="CDI">CDI (Permanent)</option>
                    <option value="CDD">CDD (Fixed-term)</option>
                    <option value="Freelance">Freelance</option>
                    <option value="Unemployed">Unemployed</option>
                  </select>
                  <label className="absolute left-4 top-1 text-xs text-muted-foreground">Contract Type</label>
                </div>
                <FloatingInput
                  label="Job Tenure (years)"
                  type="number"
                  value={clientForm.job_tenure_years}
                  onChange={(e) => setClientForm({ ...clientForm, job_tenure_years: e.target.value })}
                  required
                />
              </div>

              {/* Financial */}
              <div className="text-xs text-muted-foreground font-medium mb-2 mt-6">Financial Metrics</div>
              <div className="grid grid-cols-2 gap-4">
                <FloatingInput
                  label="Annual Income ($)"
                  type="number"
                  value={clientForm.income_annual}
                  onChange={(e) => setClientForm({ ...clientForm, income_annual: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Debt-to-Income Ratio (0-1)"
                  type="number"
                  step="0.01"
                  value={clientForm.debt_to_income_ratio}
                  onChange={(e) => setClientForm({ ...clientForm, debt_to_income_ratio: e.target.value })}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FloatingInput
                  label="Savings Rate (0-1)"
                  type="number"
                  step="0.01"
                  value={clientForm.savings_rate}
                  onChange={(e) => setClientForm({ ...clientForm, savings_rate: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Spending Volatility (0-1)"
                  type="number"
                  step="0.01"
                  value={clientForm.spending_volatility_index}
                  onChange={(e) => setClientForm({ ...clientForm, spending_volatility_index: e.target.value })}
                  required
                />
              </div>

              {/* Credit */}
              <div className="text-xs text-muted-foreground font-medium mb-2 mt-6">Credit Behavior</div>
              <div className="grid grid-cols-2 gap-4">
                <FloatingInput
                  label="Missed Payments (last 12m)"
                  type="number"
                  value={clientForm.missed_payments_last_12m}
                  onChange={(e) => setClientForm({ ...clientForm, missed_payments_last_12m: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Credit Utilization Avg (0-1)"
                  type="number"
                  step="0.01"
                  value={clientForm.credit_utilization_avg}
                  onChange={(e) => setClientForm({ ...clientForm, credit_utilization_avg: e.target.value })}
                  required
                />
              </div>
              <div className="relative">
                <select
                  value={clientForm.loan_purpose}
                  onChange={(e) => setClientForm({ ...clientForm, loan_purpose: e.target.value })}
                  className="w-full px-4 py-3 bg-secondary/50 border border-glass-border rounded-lg text-foreground focus:outline-none focus:border-primary appearance-none"
                >
                  <option value="Home renovation">Home renovation</option>
                  <option value="Debt consolidation">Debt consolidation</option>
                  <option value="Vehicle purchase">Vehicle purchase</option>
                  <option value="Medical expenses">Medical expenses</option>
                  <option value="Education">Education</option>
                  <option value="Business investment">Business investment</option>
                  <option value="Travel">Travel</option>
                </select>
                <label className="absolute left-4 top-1 text-xs text-muted-foreground">Loan Purpose</label>
              </div>
            </motion.div>
          )}

          {/* STARTUP FORM */}
          {activeTab === 'startup' && (
            <motion.div
              key="startup"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {/* Company Info */}
              <div className="text-xs text-muted-foreground font-medium mb-2">Company Information</div>
              <div className="grid grid-cols-2 gap-4">
                <div className="relative">
                  <select
                    value={startupForm.sector}
                    onChange={(e) => setStartupForm({ ...startupForm, sector: e.target.value })}
                    className="w-full px-4 py-3 bg-secondary/50 border border-glass-border rounded-lg text-foreground focus:outline-none focus:border-primary appearance-none"
                  >
                    <option value="SaaS">SaaS</option>
                    <option value="FinTech">FinTech</option>
                    <option value="HealthTech">HealthTech</option>
                    <option value="E-commerce">E-commerce</option>
                    <option value="DeepTech">DeepTech</option>
                    <option value="CleanTech">CleanTech</option>
                    <option value="EdTech">EdTech</option>
                  </select>
                  <label className="absolute left-4 top-1 text-xs text-muted-foreground">Sector</label>
                </div>
                <FloatingInput
                  label="Founder Experience (years)"
                  type="number"
                  value={startupForm.founder_experience_years}
                  onChange={(e) => setStartupForm({ ...startupForm, founder_experience_years: e.target.value })}
                  required
                />
              </div>
              <div className="flex items-center gap-3 px-4 py-3 bg-secondary/50 border border-glass-border rounded-lg">
                <input
                  type="checkbox"
                  id="vcBacking"
                  checked={startupForm.vc_backing}
                  onChange={(e) => setStartupForm({ ...startupForm, vc_backing: e.target.checked })}
                  className="w-4 h-4 rounded border-glass-border bg-secondary text-primary focus:ring-primary"
                />
                <label htmlFor="vcBacking" className="text-sm text-muted-foreground">VC Backed</label>
              </div>

              {/* Revenue */}
              <div className="text-xs text-muted-foreground font-medium mb-2 mt-6">Revenue Metrics</div>
              <div className="grid grid-cols-2 gap-4">
                <FloatingInput
                  label="ARR Current ($)"
                  type="number"
                  value={startupForm.arr_current}
                  onChange={(e) => setStartupForm({ ...startupForm, arr_current: e.target.value })}
                  required
                />
                <FloatingInput
                  label="ARR Growth YoY (0-2, e.g. 0.85 = 85%)"
                  type="number"
                  step="0.01"
                  value={startupForm.arr_growth_yoy}
                  onChange={(e) => setStartupForm({ ...startupForm, arr_growth_yoy: e.target.value })}
                  required
                />
              </div>

              {/* Burn & Runway */}
              <div className="text-xs text-muted-foreground font-medium mb-2 mt-6">Burn & Runway</div>
              <div className="grid grid-cols-2 gap-4">
                <FloatingInput
                  label="Burn Rate Monthly ($)"
                  type="number"
                  value={startupForm.burn_rate_monthly}
                  onChange={(e) => setStartupForm({ ...startupForm, burn_rate_monthly: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Runway (months)"
                  type="number"
                  step="0.1"
                  value={startupForm.runway_months}
                  onChange={(e) => setStartupForm({ ...startupForm, runway_months: e.target.value })}
                  required
                />
              </div>

              {/* Unit Economics */}
              <div className="text-xs text-muted-foreground font-medium mb-2 mt-6">Unit Economics</div>
              <div className="grid grid-cols-3 gap-4">
                <FloatingInput
                  label="CAC/LTV Ratio"
                  type="number"
                  step="0.01"
                  value={startupForm.cac_ltv_ratio}
                  onChange={(e) => setStartupForm({ ...startupForm, cac_ltv_ratio: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Churn Rate Monthly"
                  type="number"
                  step="0.001"
                  value={startupForm.churn_rate_monthly}
                  onChange={(e) => setStartupForm({ ...startupForm, churn_rate_monthly: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Burn Multiple"
                  type="number"
                  step="0.1"
                  value={startupForm.burn_multiple}
                  onChange={(e) => setStartupForm({ ...startupForm, burn_multiple: e.target.value })}
                  required
                />
              </div>
            </motion.div>
          )}

          {/* ENTERPRISE FORM */}
          {activeTab === 'enterprise' && (
            <motion.div
              key="enterprise"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {/* Company Info */}
              <div className="text-xs text-muted-foreground font-medium mb-2">Company Information</div>
              <div className="relative">
                <select
                  value={enterpriseForm.industry_code}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, industry_code: e.target.value })}
                  className="w-full px-4 py-3 bg-secondary/50 border border-glass-border rounded-lg text-foreground focus:outline-none focus:border-primary appearance-none"
                >
                  <option value="Manufacturing">Manufacturing</option>
                  <option value="Retail">Retail</option>
                  <option value="Technology">Technology</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Energy">Energy</option>
                  <option value="Financial Services">Financial Services</option>
                  <option value="Real Estate">Real Estate</option>
                  <option value="Transportation">Transportation</option>
                </select>
                <label className="absolute left-4 top-1 text-xs text-muted-foreground">Industry</label>
              </div>

              {/* Financials */}
              <div className="text-xs text-muted-foreground font-medium mb-2 mt-6">Financial Metrics</div>
              <div className="grid grid-cols-2 gap-4">
                <FloatingInput
                  label="Annual Revenue ($)"
                  type="number"
                  value={enterpriseForm.revenue_annual}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, revenue_annual: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Net Profit Margin (-0.05 to 0.25)"
                  type="number"
                  step="0.01"
                  value={enterpriseForm.net_profit_margin}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, net_profit_margin: e.target.value })}
                  required
                />
              </div>

              {/* Ratios */}
              <div className="text-xs text-muted-foreground font-medium mb-2 mt-6">Financial Ratios</div>
              <div className="grid grid-cols-2 gap-4">
                <FloatingInput
                  label="Current Ratio"
                  type="number"
                  step="0.01"
                  value={enterpriseForm.current_ratio}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, current_ratio: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Quick Ratio"
                  type="number"
                  step="0.01"
                  value={enterpriseForm.quick_ratio}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, quick_ratio: e.target.value })}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FloatingInput
                  label="Debt-to-Equity"
                  type="number"
                  step="0.01"
                  value={enterpriseForm.debt_to_equity}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, debt_to_equity: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Interest Coverage Ratio"
                  type="number"
                  step="0.1"
                  value={enterpriseForm.interest_coverage_ratio}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, interest_coverage_ratio: e.target.value })}
                  required
                />
              </div>

              {/* Risk Indicators */}
              <div className="text-xs text-muted-foreground font-medium mb-2 mt-6">Risk Indicators</div>
              <div className="grid grid-cols-3 gap-4">
                <FloatingInput
                  label="Altman Z-Score (-1 to 5)"
                  type="number"
                  step="0.01"
                  value={enterpriseForm.altman_z_score}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, altman_z_score: e.target.value })}
                  required
                />
                <FloatingInput
                  label="ESG Risk Score (30-95)"
                  type="number"
                  step="0.1"
                  value={enterpriseForm.esg_risk_score}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, esg_risk_score: e.target.value })}
                  required
                />
                <FloatingInput
                  label="Active Lawsuits"
                  type="number"
                  value={enterpriseForm.legal_lawsuits_active}
                  onChange={(e) => setEnterpriseForm({ ...enterpriseForm, legal_lawsuits_active: e.target.value })}
                  required
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-8">
          <GradientButton
            type="submit"
            size="lg"
            loading={isLoading}
            className="w-full"
          >
            🚀 Run Multi-Agent Analysis
          </GradientButton>
        </div>
      </form>
    </GlassCard>
  );
};
