import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { StatusPulse } from "@/components/ui/StatusPulse";
import { ApplicationForm } from "@/components/ApplicationForm";
import { AnalysisLoading } from "@/components/AnalysisLoading";
import { DecisionHero } from "@/components/DecisionHero";
import { AgentCard } from "@/components/AgentCard";
import { HistorySidebar } from "@/components/HistorySidebar";
import { EvidenceGraph } from "@/components/EvidenceGraph";
import { GradientButton } from "@/components/ui/GradientButton";
import { OnDemandAgentPanel } from "@/components/OnDemandAgentPanel";
import { RegulationChatbot } from "@/components/RegulationChatbot";
import { Application, DecisionResult, AgentVerdict } from "@/types/application";
import { submitDecision, ApiDecisionResponse, checkHealth } from "@/lib/api";
import { ArrowLeft, Zap, Wifi, WifiOff } from "lucide-react";
import { useEffect } from "react";

type ViewState = 'form' | 'loading' | 'result';

// Transform API response to frontend types
const transformApiResponse = (api: ApiDecisionResponse): DecisionResult => {
  const agentColorMap: Record<string, 'risk' | 'fairness' | 'trajectory'> = {
    'RiskAgent': 'risk',
    'FairnessAgent': 'fairness',
    'TrajectoryAgent': 'trajectory',
  };

  const transformVerdict = (
    verdict: typeof api.risk_verdict,
    fallbackName: string,
    color: 'risk' | 'fairness' | 'trajectory',
    role: string
  ): AgentVerdict | null => {
    if (!verdict) return null;
    return {
      agentName: verdict.agent_name || fallbackName,
      agentRole: role,
      agentColor: agentColorMap[verdict.agent_name] || color,
      recommendation: verdict.recommendation === 'ESCALATE' ? 'CAUTION' : verdict.recommendation as any,
      reasoning: verdict.reasoning,
      concerns: verdict.key_concerns || [],
      mitigatingFactors: verdict.mitigating_factors || [],
      confidence: verdict.confidence === 'HIGH' ? 90 : verdict.confidence === 'MEDIUM' ? 70 : 50,
      similarCases: (verdict.evidence || []).slice(0, 3).map(e => ({
        entityId: e.entity_id,
        outcome: e.outcome as any,
        similarity: Math.round((e.similarity_score || 0) * 100),
        reasoning: e.key_factors?.join(', ') || '',
      })),
    };
  };

  const agents: AgentVerdict[] = [
    transformVerdict(api.risk_verdict, 'Risk Agent', 'risk', 'The Prosecutor'),
    transformVerdict(api.fairness_verdict, 'Fairness Agent', 'fairness', 'The Advocate'),
    transformVerdict(api.trajectory_verdict, 'Trajectory Agent', 'trajectory', 'The Predictor'),
  ].filter((a): a is AgentVerdict => a !== null);

  return {
    decision: api.final_decision.recommendation,
    confidence: api.final_decision.confidence === 'HIGH' ? 92 : api.final_decision.confidence === 'MEDIUM' ? 75 : 55,
    processingTime: Math.round(api.processing_time_ms / 100) / 10, // Convert to seconds
    agents,
    summary: api.final_decision.reasoning,
    applicationId: api.decision_id,
  };
};

export const Dashboard = () => {
  const [view, setView] = useState<ViewState>('form');
  const [currentAgent, setCurrentAgent] = useState(0);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<DecisionResult | null>(null);
  const [decisionId, setDecisionId] = useState<string | null>(null);
  const [application, setApplication] = useState<Application | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(true);

  // Check API health on mount
  useEffect(() => {
    const checkConnection = async () => {
      const healthy = await checkHealth();
      setIsConnected(healthy);
    };
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  const runAnalysis = useCallback(async (app: Application) => {
    setApplication(app);
    setView('loading');
    setCurrentAgent(0);
    setProgress(0);
    setError(null);

    // Animate through agents while waiting for API
    const agentDuration = 2500;
    const agents = [0, 1, 2, 3];

    agents.forEach((agentIndex, i) => {
      setTimeout(() => {
        setCurrentAgent(agentIndex);
        setProgress(((agentIndex + 1) / 4) * 90); // Leave 10% for final
      }, i * agentDuration);
    });

    try {
      // Build API request
      const request = buildApiRequest(app);

      // Call real API
      const apiResponse = await submitDecision(request);

      // Transform and display result
      setProgress(100);
      const transformedResult = transformApiResponse(apiResponse);
      setResult(transformedResult);
      setDecisionId(apiResponse.decision_id);

      setTimeout(() => setView('result'), 500);
    } catch (err) {
      console.error('API Error:', err);
      setError(err instanceof Error ? err.message : 'Failed to analyze application');
      setView('form');
    }
  }, []);

  const handleNewAnalysis = () => {
    setView('form');
    setResult(null);
    setDecisionId(null);
    setApplication(null);
    setCurrentAgent(0);
    setProgress(0);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-glass-border bg-card/30 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-agent-trajectory flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold gradient-text bg-gradient-to-r from-primary to-agent-trajectory">
                    FairTrace
                  </h1>
                  <p className="text-xs text-muted-foreground">Multi-Agent Credit Intelligence</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {isConnected ? (
                <StatusPulse status="connected" label="API Connected" />
              ) : (
                <div className="flex items-center gap-2 text-destructive">
                  <WifiOff className="w-4 h-4" />
                  <span className="text-xs">API Disconnected</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Error Alert */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 bg-destructive/10 border border-destructive/30 rounded-lg text-destructive"
          >
            <p className="font-medium">Error: {error}</p>
            <p className="text-sm opacity-80">Please try again or check if the backend is running.</p>
          </motion.div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Area */}
          <div className="lg:col-span-2">
            <AnimatePresence mode="wait">
              {view === 'form' && (
                <motion.div
                  key="form"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <ApplicationForm
                    onSubmit={runAnalysis}
                    isLoading={false}
                  />
                </motion.div>
              )}

              {view === 'loading' && (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="bg-card/60 backdrop-blur-xl border border-glass-border rounded-xl"
                >
                  <AnalysisLoading
                    currentAgent={currentAgent}
                    progress={progress}
                  />
                </motion.div>
              )}

              {view === 'result' && result && (
                <motion.div
                  key="result"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-6"
                >
                  {/* Back Button */}
                  <GradientButton
                    variant="primary"
                    size="sm"
                    onClick={handleNewAnalysis}
                    className="mb-4"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    New Application
                  </GradientButton>

                  {/* Decision Hero */}
                  <DecisionHero result={result} />

                  {/* Agent Cards */}
                  <div>
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <span>Agent Analysis</span>
                      <span className="text-xs text-muted-foreground font-normal">
                        ({result.agents.length} agents evaluated)
                      </span>
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {result.agents.map((agent, index) => (
                        <AgentCard
                          key={agent.agentName}
                          verdict={agent}
                          index={index}
                        />
                      ))}
                    </div>
                  </div>

                  {/* On-Demand Agent Panels */}
                  {decisionId && (
                    <OnDemandAgentPanel decisionId={decisionId} />
                  )}

                  {/* Evidence Graph */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4, duration: 0.4 }}
                  >
                    <EvidenceGraph agents={result.agents} />
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            <HistorySidebar />
          </div>
        </div>
      </main>

      {/* Regulation Chatbot - Hidden during loading */}
      {view !== 'loading' && <RegulationChatbot />}
    </div>
  );
};

// Helper to build API request from frontend Application type
function buildApiRequest(app: Application): { application_type: 'client' | 'startup' | 'enterprise'; application: Record<string, unknown> } {
  if (app.type === 'startup') {
    return {
      application_type: 'startup' as const,
      application: {
        sector: app.sector,
        founder_experience_years: app.founder_experience_years,
        vc_backing: app.vc_backing,
        arr_current: app.arr_current,
        arr_growth_yoy: app.arr_growth_yoy,
        burn_rate_monthly: app.burn_rate_monthly,
        runway_months: app.runway_months,
        cac_ltv_ratio: app.cac_ltv_ratio,
        churn_rate_monthly: app.churn_rate_monthly,
        burn_multiple: app.burn_multiple,
      },
    };
  } else if (app.type === 'client') {
    return {
      application_type: 'client' as const,
      application: {
        age: app.age,
        contract_type: app.contract_type,
        job_tenure_years: app.job_tenure_years,
        income_annual: app.income_annual,
        debt_to_income_ratio: app.debt_to_income_ratio,
        savings_rate: app.savings_rate,
        spending_volatility_index: app.spending_volatility_index,
        missed_payments_last_12m: app.missed_payments_last_12m,
        credit_utilization_avg: app.credit_utilization_avg,
        loan_purpose: app.loan_purpose,
      },
    };
  } else {
    return {
      application_type: 'enterprise' as const,
      application: {
        industry_code: app.industry_code,
        revenue_annual: app.revenue_annual,
        net_profit_margin: app.net_profit_margin,
        current_ratio: app.current_ratio,
        quick_ratio: app.quick_ratio,
        debt_to_equity: app.debt_to_equity,
        interest_coverage_ratio: app.interest_coverage_ratio,
        altman_z_score: app.altman_z_score,
        esg_risk_score: app.esg_risk_score,
        legal_lawsuits_active: app.legal_lawsuits_active,
      },
    };
  }
}
