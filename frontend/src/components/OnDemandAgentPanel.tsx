import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "@/components/ui/GlassCard";
import { GradientButton } from "@/components/ui/GradientButton";
import {
    getAdvisorAnalysis,
    getNarrativeAnalysis,
    getComparatorAnalysis,
    getScenarioAnalysis,
    ApiAdvisorResponse,
    ApiNarrativeResponse,
    ApiComparatorResponse,
    ApiScenarioResponse
} from "@/lib/api";
import {
    Lightbulb,
    BookOpen,
    BarChart3,
    GitBranch,
    ChevronDown,
    ChevronUp,
    Loader2,
    TrendingUp,
    TrendingDown,
    AlertCircle,
    CheckCircle,
    Target,
    Rocket
} from "lucide-react";
import { cn } from "@/lib/utils";

interface OnDemandAgentPanelProps {
    decisionId: string;
}

type AgentType = 'advisor' | 'narrative' | 'comparator' | 'scenario';

interface AgentConfig {
    id: AgentType;
    name: string;
    icon: React.ReactNode;
    color: string;
    description: string;
}

const agents: AgentConfig[] = [
    {
        id: 'advisor',
        name: 'Advisor Agent',
        icon: <Lightbulb className="w-5 h-5" />,
        color: 'from-yellow-500 to-orange-500',
        description: 'Get improvement recommendations'
    },
    {
        id: 'narrative',
        name: 'Narrative Agent',
        icon: <BookOpen className="w-5 h-5" />,
        color: 'from-purple-500 to-pink-500',
        description: 'Historical stories & patterns'
    },
    {
        id: 'comparator',
        name: 'Comparator Agent',
        icon: <BarChart3 className="w-5 h-5" />,
        color: 'from-blue-500 to-cyan-500',
        description: 'Gap analysis vs. approved cases'
    },
    {
        id: 'scenario',
        name: 'Scenario Agent',
        icon: <GitBranch className="w-5 h-5" />,
        color: 'from-green-500 to-emerald-500',
        description: 'What-if scenario modeling'
    },
];

export const OnDemandAgentPanel = ({ decisionId }: OnDemandAgentPanelProps) => {
    const [expandedAgent, setExpandedAgent] = useState<AgentType | null>(null);
    const [loadingAgent, setLoadingAgent] = useState<AgentType | null>(null);
    const [advisorData, setAdvisorData] = useState<ApiAdvisorResponse | null>(null);
    const [narrativeData, setNarrativeData] = useState<ApiNarrativeResponse | null>(null);
    const [comparatorData, setComparatorData] = useState<ApiComparatorResponse | null>(null);
    const [scenarioData, setScenarioData] = useState<ApiScenarioResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Custom scenario state
    const [customScenarios, setCustomScenarios] = useState<Array<{
        description: string;
        changes: Array<{ metric: string; to_value: string }>;
    }>>([]);
    const [newScenarioDesc, setNewScenarioDesc] = useState('');
    const [newMetric, setNewMetric] = useState('');
    const [newValue, setNewValue] = useState('');

    const handleAgentClick = async (agentId: AgentType) => {
        // Toggle expand/collapse without clearing data
        if (expandedAgent === agentId) {
            setExpandedAgent(null);
            return;
        }

        setExpandedAgent(agentId);
        setError(null);

        // Skip auto-loading for scenario agent - it requires explicit button click
        if (agentId === 'scenario') {
            return;
        }

        // Check if data already loaded - don't reload
        if (agentId === 'advisor' && advisorData) return;
        if (agentId === 'narrative' && narrativeData) return;
        if (agentId === 'comparator' && comparatorData) return;

        await loadAgentData(agentId);
    };

    const loadAgentData = async (agentId: AgentType, scenarios?: typeof customScenarios) => {
        setLoadingAgent(agentId);

        try {
            switch (agentId) {
                case 'advisor':
                    const advisorResult = await getAdvisorAnalysis(decisionId);
                    setAdvisorData(advisorResult);
                    break;
                case 'narrative':
                    const narrativeResult = await getNarrativeAnalysis(decisionId);
                    setNarrativeData(narrativeResult);
                    break;
                case 'comparator':
                    const comparatorResult = await getComparatorAnalysis(decisionId);
                    setComparatorData(comparatorResult);
                    break;
                case 'scenario':
                    const scenarioResult = await getScenarioAnalysis(
                        decisionId,
                        scenarios && scenarios.length > 0 ? scenarios : undefined
                    );
                    setScenarioData(scenarioResult);
                    break;
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load agent data');
        } finally {
            setLoadingAgent(null);
        }
    };

    const runScenarioAnalysis = async () => {
        setError(null);
        // Clear previous scenario data to show loading
        setScenarioData(null);
        await loadAgentData('scenario', customScenarios);
    };

    const addScenario = () => {
        if (!newScenarioDesc.trim()) return;
        setCustomScenarios([...customScenarios, {
            description: newScenarioDesc,
            changes: []
        }]);
        setNewScenarioDesc('');
    };

    const removeScenario = (index: number) => {
        setCustomScenarios(customScenarios.filter((_, i) => i !== index));
    };

    const addMetricChange = (scenarioIndex: number) => {
        if (!newMetric.trim() || !newValue.trim()) return;
        const updated = [...customScenarios];
        updated[scenarioIndex].changes.push({ metric: newMetric, to_value: newValue });
        setCustomScenarios(updated);
        setNewMetric('');
        setNewValue('');
    };

    const removeMetricChange = (scenarioIndex: number, changeIndex: number) => {
        const updated = [...customScenarios];
        updated[scenarioIndex].changes = updated[scenarioIndex].changes.filter((_, i) => i !== changeIndex);
        setCustomScenarios(updated);
    };

    const renderAgentContent = (agentId: AgentType) => {
        if (loadingAgent === agentId) {
            return (
                <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                    <span className="ml-2 text-muted-foreground">Analyzing...</span>
                </div>
            );
        }

        if (error && expandedAgent === agentId) {
            return (
                <div className="py-4 text-center text-destructive">
                    <AlertCircle className="w-6 h-6 mx-auto mb-2" />
                    <p>{error}</p>
                </div>
            );
        }

        switch (agentId) {
            case 'advisor':
                return advisorData ? <AdvisorContent data={advisorData} /> : null;
            case 'narrative':
                return narrativeData ? <NarrativeContent data={narrativeData} /> : null;
            case 'comparator':
                return comparatorData ? <ComparatorContent data={comparatorData} /> : null;
            case 'scenario':
                return (
                    <div className="space-y-4">
                        {/* Scenario Builder */}
                        <div className="p-4 bg-secondary/20 rounded-lg border border-glass-border">
                            <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                                <GitBranch className="w-4 h-4" />
                                Custom Scenarios (Optional)
                            </h4>

                            {/* Add new scenario */}
                            <div className="flex gap-2 mb-3">
                                <input
                                    type="text"
                                    placeholder="Scenario description (e.g., 'Income increases by 20%')"
                                    value={newScenarioDesc}
                                    onChange={(e) => setNewScenarioDesc(e.target.value)}
                                    className="flex-1 px-3 py-2 text-sm bg-background border border-glass-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    onKeyDown={(e) => e.key === 'Enter' && addScenario()}
                                />
                                <button
                                    onClick={addScenario}
                                    className="px-3 py-2 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg text-sm font-medium transition-colors"
                                >
                                    + Add
                                </button>
                            </div>

                            {/* List of custom scenarios */}
                            {customScenarios.length > 0 && (
                                <div className="space-y-2 mb-3">
                                    {customScenarios.map((scenario, idx) => (
                                        <div key={idx} className="p-3 bg-background/50 rounded-lg border border-glass-border">
                                            <div className="flex items-start justify-between mb-2">
                                                <span className="text-sm font-medium">{scenario.description}</span>
                                                <button
                                                    onClick={() => removeScenario(idx)}
                                                    className="text-destructive hover:text-destructive/80 text-xs"
                                                >
                                                    Remove
                                                </button>
                                            </div>

                                            {/* Metric changes */}
                                            {scenario.changes.length > 0 && (
                                                <div className="flex flex-wrap gap-1 mb-2">
                                                    {scenario.changes.map((change, cIdx) => (
                                                        <span
                                                            key={cIdx}
                                                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary/10 text-primary text-xs rounded-full"
                                                        >
                                                            {change.metric}: {change.to_value}
                                                            <button
                                                                onClick={() => removeMetricChange(idx, cIdx)}
                                                                className="hover:text-destructive"
                                                            >
                                                                ×
                                                            </button>
                                                        </span>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Add metric change */}
                                            <div className="flex gap-1">
                                                <input
                                                    type="text"
                                                    placeholder="Metric"
                                                    value={newMetric}
                                                    onChange={(e) => setNewMetric(e.target.value)}
                                                    className="w-28 px-2 py-1 text-xs bg-background border border-glass-border rounded"
                                                />
                                                <input
                                                    type="text"
                                                    placeholder="New value"
                                                    value={newValue}
                                                    onChange={(e) => setNewValue(e.target.value)}
                                                    className="w-24 px-2 py-1 text-xs bg-background border border-glass-border rounded"
                                                />
                                                <button
                                                    onClick={() => addMetricChange(idx)}
                                                    className="px-2 py-1 text-xs bg-secondary hover:bg-secondary/80 rounded"
                                                >
                                                    + Metric
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <p className="text-xs text-muted-foreground">
                                {customScenarios.length === 0
                                    ? "Leave empty to auto-generate scenarios based on application data."
                                    : `${customScenarios.length} custom scenario(s) defined.`}
                            </p>
                        </div>

                        {/* Run button */}
                        <div className="text-center">
                            <GradientButton
                                variant="primary"
                                onClick={runScenarioAnalysis}
                                disabled={loadingAgent === 'scenario'}
                            >
                                {loadingAgent === 'scenario' ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                        Analyzing Scenarios...
                                    </>
                                ) : (
                                    <>
                                        <GitBranch className="w-4 h-4 mr-2" />
                                        {scenarioData ? 'Re-run Analysis' : 'Run Scenario Analysis'}
                                    </>
                                )}
                            </GradientButton>
                        </div>

                        {/* Results */}
                        {scenarioData && <ScenarioContent data={scenarioData} />}
                    </div>
                );
            default:
                return null;
        }
    };

    // Check if agent has loaded data
    const hasData = (agentId: AgentType) => {
        switch (agentId) {
            case 'advisor': return !!advisorData;
            case 'narrative': return !!narrativeData;
            case 'comparator': return !!comparatorData;
            case 'scenario': return !!scenarioData;
            default: return false;
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
        >
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Rocket className="w-5 h-5 text-primary" />
                <span>On-Demand Insights</span>
                <span className="text-xs text-muted-foreground font-normal">
                    (Click to explore)
                </span>
            </h2>

            <div className="space-y-3">
                {agents.map((agent) => (
                    <GlassCard key={agent.id} className="overflow-hidden" hover={false}>
                        <button
                            onClick={() => handleAgentClick(agent.id)}
                            className="w-full p-4 flex items-center justify-between hover:bg-secondary/30 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <div className={cn(
                                    "w-10 h-10 rounded-lg bg-gradient-to-br flex items-center justify-center text-white",
                                    agent.color
                                )}>
                                    {agent.icon}
                                </div>
                                <div className="text-left">
                                    <h3 className="font-medium flex items-center gap-2">
                                        {agent.name}
                                        {hasData(agent.id) && (
                                            <CheckCircle className="w-4 h-4 text-success" />
                                        )}
                                    </h3>
                                    <p className="text-xs text-muted-foreground">{agent.description}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {loadingAgent === agent.id && (
                                    <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                                )}
                                {expandedAgent === agent.id ? (
                                    <ChevronUp className="w-5 h-5 text-muted-foreground" />
                                ) : (
                                    <ChevronDown className="w-5 h-5 text-muted-foreground" />
                                )}
                            </div>
                        </button>

                        <AnimatePresence>
                            {expandedAgent === agent.id && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: "auto", opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="overflow-hidden"
                                >
                                    <div className="px-4 pb-4 border-t border-glass-border pt-4">
                                        {renderAgentContent(agent.id)}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </GlassCard>
                ))}
            </div>
        </motion.div>
    );
};

// Sub-components for each agent type
const AdvisorContent = ({ data }: { data: ApiAdvisorResponse }) => (
    <div className="space-y-4">
        <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Outlook:</span>
            <span className={cn(
                "px-2 py-0.5 rounded text-xs font-medium",
                data.overall_outlook === 'EXCELLENT' && 'bg-success/20 text-success',
                data.overall_outlook === 'PROMISING' && 'bg-success/20 text-success',
                data.overall_outlook === 'FAIR' && 'bg-warning/20 text-warning',
                data.overall_outlook === 'POOR' && 'bg-destructive/20 text-destructive',
            )}>
                {data.overall_outlook}
            </span>
        </div>

        {data.improvement_areas.length > 0 && (
            <div>
                <h4 className="text-sm font-medium mb-2">Improvement Areas</h4>
                <div className="space-y-2">
                    {data.improvement_areas.map((area, i) => (
                        <div key={i} className="p-2 bg-secondary/30 rounded-lg">
                            <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-sm">{area.area}</span>
                                <span className={cn(
                                    "text-xs px-2 py-0.5 rounded",
                                    area.priority === 'HIGH' && 'bg-destructive/20 text-destructive',
                                    area.priority === 'MEDIUM' && 'bg-warning/20 text-warning',
                                    area.priority === 'LOW' && 'bg-success/20 text-success',
                                )}>
                                    {area.priority}
                                </span>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span>{area.current_state}</span>
                                <TrendingUp className="w-3 h-3" />
                                <span className="text-success">{area.target_state}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )}

        {data.recommendations.length > 0 && (
            <div>
                <h4 className="text-sm font-medium mb-2">Recommendations</h4>
                <div className="space-y-2">
                    {data.recommendations.slice(0, 3).map((rec, i) => (
                        <div key={i} className="p-3 bg-secondary/30 rounded-lg">
                            <div className="flex items-start gap-2">
                                <Target className="w-4 h-4 text-primary mt-0.5" />
                                <div>
                                    <p className="text-sm font-medium">{rec.action}</p>
                                    <p className="text-xs text-muted-foreground mt-1">{rec.rationale}</p>
                                    <div className="flex gap-3 mt-2 text-xs">
                                        <span className="text-muted-foreground">⏱ {rec.timeline}</span>
                                        <span className={cn(
                                            rec.expected_impact === 'HIGH' && 'text-success',
                                            rec.expected_impact === 'MEDIUM' && 'text-warning',
                                            rec.expected_impact === 'LOW' && 'text-muted-foreground',
                                        )}>
                                            Impact: {rec.expected_impact}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )}
    </div>
);

const NarrativeContent = ({ data }: { data: ApiNarrativeResponse }) => (
    <div className="space-y-4">
        <p className="text-sm text-muted-foreground">{data.narrative_summary}</p>

        {data.key_patterns.length > 0 && (
            <div>
                <h4 className="text-sm font-medium mb-2">Key Patterns</h4>
                <div className="flex flex-wrap gap-2">
                    {data.key_patterns.slice(0, 4).map((pattern, i) => (
                        <span
                            key={i}
                            className={cn(
                                "px-2 py-1 rounded-full text-xs",
                                pattern.impact === 'POSITIVE' && 'bg-success/20 text-success',
                                pattern.impact === 'NEGATIVE' && 'bg-destructive/20 text-destructive',
                                pattern.impact === 'NEUTRAL' && 'bg-secondary text-muted-foreground',
                            )}
                        >
                            {pattern.pattern}
                        </span>
                    ))}
                </div>
            </div>
        )}

        {data.success_stories.length > 0 && (
            <div>
                <h4 className="text-sm font-medium mb-2 flex items-center gap-1">
                    <CheckCircle className="w-4 h-4 text-success" /> Success Stories
                </h4>
                {data.success_stories.slice(0, 2).map((story, i) => (
                    <div key={i} className="p-2 bg-success/10 border border-success/20 rounded-lg mb-2">
                        <p className="font-medium text-sm">{story.title}</p>
                        <p className="text-xs text-muted-foreground">{story.summary}</p>
                    </div>
                ))}
            </div>
        )}

        {data.lessons_learned.length > 0 && (
            <div>
                <h4 className="text-sm font-medium mb-2">Lessons Learned</h4>
                <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                    {data.lessons_learned.slice(0, 3).map((lesson, i) => (
                        <li key={i}>{lesson}</li>
                    ))}
                </ul>
            </div>
        )}
    </div>
);

const ComparatorContent = ({ data }: { data: ApiComparatorResponse }) => (
    <div className="space-y-4">
        <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Gap Score:</span>
            <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-secondary rounded-full overflow-hidden">
                    <div
                        className={cn(
                            "h-full rounded-full",
                            data.overall_gap_score <= 30 && 'bg-success',
                            data.overall_gap_score > 30 && data.overall_gap_score <= 60 && 'bg-warning',
                            data.overall_gap_score > 60 && 'bg-destructive',
                        )}
                        style={{ width: `${100 - data.overall_gap_score}%` }}
                    />
                </div>
                <span className="text-sm font-medium">{100 - Math.round(data.overall_gap_score)}%</span>
            </div>
        </div>

        <p className="text-sm text-muted-foreground">{data.executive_summary}</p>

        {data.metric_comparisons.length > 0 && (
            <div>
                <h4 className="text-sm font-medium mb-2">Metric Comparison</h4>
                <div className="space-y-2">
                    {data.metric_comparisons.slice(0, 4).map((mc, i) => (
                        <div key={i} className="flex items-center justify-between p-2 bg-secondary/30 rounded">
                            <span className="text-sm">{mc.metric_name}</span>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">{mc.applicant_value}</span>
                                {mc.status === 'ABOVE_AVERAGE' && <TrendingUp className="w-4 h-4 text-success" />}
                                {mc.status === 'BELOW_AVERAGE' && <TrendingDown className="w-4 h-4 text-warning" />}
                                {mc.status === 'CRITICAL_GAP' && <TrendingDown className="w-4 h-4 text-destructive" />}
                                {mc.status === 'AT_AVERAGE' && <span className="text-muted-foreground">—</span>}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )}

        {data.gaps.length > 0 && (
            <div>
                <h4 className="text-sm font-medium mb-2">Critical Gaps</h4>
                <div className="space-y-1">
                    {data.gaps.filter(g => g.gap_severity !== 'MINOR').slice(0, 3).map((gap, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm">
                            <AlertCircle className={cn(
                                "w-4 h-4 mt-0.5",
                                gap.gap_severity === 'CRITICAL' && 'text-destructive',
                                gap.gap_severity === 'SIGNIFICANT' && 'text-warning',
                                gap.gap_severity === 'MODERATE' && 'text-muted-foreground',
                            )} />
                            <span className="text-muted-foreground">{gap.description}</span>
                        </div>
                    ))}
                </div>
            </div>
        )}
    </div>
);

const ScenarioContent = ({ data }: { data: ApiScenarioResponse }) => (
    <div className="space-y-4">
        <div className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg">
            <div>
                <span className="text-xs text-muted-foreground">Current Probability</span>
                <p className="text-2xl font-bold">{Math.round(data.current_assessment.approval_probability)}%</p>
            </div>
            <span className={cn(
                "px-2 py-1 rounded text-xs font-medium",
                data.current_assessment.current_outcome === 'LIKELY_APPROVE' && 'bg-success/20 text-success',
                data.current_assessment.current_outcome === 'BORDERLINE' && 'bg-warning/20 text-warning',
                data.current_assessment.current_outcome === 'LIKELY_REJECT' && 'bg-destructive/20 text-destructive',
            )}>
                {data.current_assessment.current_outcome.replace('_', ' ')}
            </span>
        </div>

        {data.scenarios.length > 0 && (
            <div>
                <h4 className="text-sm font-medium mb-2">What-If Scenarios</h4>
                <div className="space-y-2">
                    {data.scenarios.slice(0, 3).map((scenario, i) => (
                        <div key={i} className="p-3 bg-secondary/30 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                                <span className="font-medium text-sm">{scenario.scenario_name}</span>
                                <div className="flex items-center gap-1">
                                    <TrendingUp className={cn(
                                        "w-4 h-4",
                                        scenario.probability_change > 0 ? 'text-success' : 'text-destructive'
                                    )} />
                                    <span className={cn(
                                        "text-sm font-medium",
                                        scenario.probability_change > 0 ? 'text-success' : 'text-destructive'
                                    )}>
                                        {scenario.probability_change > 0 ? '+' : ''}{Math.round(scenario.probability_change)}%
                                    </span>
                                </div>
                            </div>
                            <div className="flex gap-3 text-xs text-muted-foreground">
                                <span>→ {scenario.new_probability}% approval</span>
                                <span>⏱ {scenario.timeframe}</span>
                                <span className={cn(
                                    scenario.feasibility === 'EASY' && 'text-success',
                                    scenario.feasibility === 'MODERATE' && 'text-warning',
                                    (scenario.feasibility === 'DIFFICULT' || scenario.feasibility === 'VERY_DIFFICULT') && 'text-destructive',
                                )}>
                                    {scenario.feasibility}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )}

        {data.optimal_path && (
            <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg">
                <h4 className="text-sm font-medium mb-2 flex items-center gap-1">
                    <Rocket className="w-4 h-4 text-primary" /> Optimal Path
                </h4>
                <p className="text-sm text-muted-foreground mb-2">{data.optimal_path.description}</p>
                <div className="text-xs">
                    Success Probability: <span className="font-medium text-success">{data.optimal_path.success_probability}%</span>
                </div>
            </div>
        )}
    </div>
);
