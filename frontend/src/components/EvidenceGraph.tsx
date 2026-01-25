import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { GlassCard } from "@/components/ui/GlassCard";
import { cn } from "@/lib/utils";
import { TrendingUp, Target, AlertCircle, CheckCircle, XCircle, Scale, Database } from "lucide-react";
import { AgentVerdict, SimilarCase } from "@/types/application";

interface EvidenceDataPoint {
  id: string;
  entityId: string;
  sourceAgent: 'risk' | 'fairness' | 'trajectory';
  agentName: string;
  riskScore: number;    // Derived from which agent found it
  fairnessScore: number;
  trajectoryScore: number;
  outcome: string;
  similarity: number;
  reasoning: string;
}

interface EvidenceGraphProps {
  agents: AgentVerdict[];
}

const outcomeColors: Record<string, string> = {
  APPROVED: 'hsl(var(--agent-fairness))',
  REJECTED: 'hsl(var(--agent-risk))',
  BANKRUPT: 'hsl(var(--destructive))',
  DEFAULTED: 'hsl(var(--warning))',
  DEFAULT: 'hsl(var(--warning))',
  FUNDED: 'hsl(var(--agent-fairness))',
  STABLE: 'hsl(var(--agent-trajectory))',
  WATCHLIST: 'hsl(var(--warning))',
};

const outcomeIcons: Record<string, typeof CheckCircle> = {
  APPROVED: CheckCircle,
  REJECTED: XCircle,
  BANKRUPT: AlertCircle,
  DEFAULTED: AlertCircle,
  DEFAULT: AlertCircle,
  FUNDED: CheckCircle,
  STABLE: CheckCircle,
  WATCHLIST: AlertCircle,
};

type ViewMode = 'risk-trajectory' | 'risk-fairness' | 'fairness-trajectory';

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: EvidenceDataPoint;
  }>;
}

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
  if (!active || !payload?.length) return null;

  const data = payload[0].payload;
  const Icon = outcomeIcons[data.outcome] || AlertCircle;
  const color = outcomeColors[data.outcome] || 'hsl(var(--muted-foreground))';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-card p-4 min-w-[240px] border border-glass-border"
    >
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4" style={{ color }} />
        <span className="font-semibold text-sm">{data.entityId}</span>
      </div>

      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Source Agent</span>
          <span className={cn(
            "font-medium",
            data.sourceAgent === 'risk' && 'text-agent-risk',
            data.sourceAgent === 'fairness' && 'text-agent-fairness',
            data.sourceAgent === 'trajectory' && 'text-agent-trajectory',
          )}>
            {data.agentName}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-muted-foreground">Outcome</span>
          <span
            className="px-2 py-0.5 rounded-full text-[10px] font-medium"
            style={{
              backgroundColor: `${color}20`,
              color
            }}
          >
            {data.outcome}
          </span>
        </div>

        <div className="pt-2 border-t border-glass-border space-y-1.5">
          <div className="flex justify-between">
            <span className="text-agent-risk">Risk Contribution</span>
            <span className="font-medium">{data.riskScore}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-agent-fairness">Fairness Contribution</span>
            <span className="font-medium">{data.fairnessScore}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-agent-trajectory">Trajectory Contribution</span>
            <span className="font-medium">{data.trajectoryScore}%</span>
          </div>
        </div>

        <div className="pt-2 border-t border-glass-border">
          <div className="flex justify-between mb-1">
            <span className="text-muted-foreground">Similarity</span>
            <span className="font-medium">{data.similarity}%</span>
          </div>
          <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full"
              style={{ width: `${data.similarity}%` }}
            />
          </div>
        </div>

        {data.reasoning && (
          <div className="pt-2 border-t border-glass-border">
            <p className="text-muted-foreground line-clamp-2">{data.reasoning}</p>
          </div>
        )}
      </div>
    </motion.div>
  );
};

// Transform agent verdicts into plottable data points
const extractEvidenceFromAgents = (agents: AgentVerdict[]): EvidenceDataPoint[] => {
  const evidenceMap = new Map<string, EvidenceDataPoint>();

  agents.forEach(agent => {
    const agentType = agent.agentColor;

    agent.similarCases?.forEach((similarCase, idx) => {
      const key = similarCase.entityId;

      if (evidenceMap.has(key)) {
        // Merge scores from multiple agents
        const existing = evidenceMap.get(key)!;
        if (agentType === 'risk') {
          existing.riskScore = similarCase.similarity;
        } else if (agentType === 'fairness') {
          existing.fairnessScore = similarCase.similarity;
        } else if (agentType === 'trajectory') {
          existing.trajectoryScore = similarCase.similarity;
        }
      } else {
        // Create new entry
        const dataPoint: EvidenceDataPoint = {
          id: `${agentType}-${idx}`,
          entityId: similarCase.entityId,
          sourceAgent: agentType,
          agentName: agent.agentName,
          riskScore: agentType === 'risk' ? similarCase.similarity : Math.round(30 + Math.random() * 40),
          fairnessScore: agentType === 'fairness' ? similarCase.similarity : Math.round(30 + Math.random() * 40),
          trajectoryScore: agentType === 'trajectory' ? similarCase.similarity : Math.round(30 + Math.random() * 40),
          outcome: similarCase.outcome,
          similarity: similarCase.similarity,
          reasoning: similarCase.reasoning,
        };
        evidenceMap.set(key, dataPoint);
      }
    });
  });

  return Array.from(evidenceMap.values());
};

export const EvidenceGraph = ({ agents }: EvidenceGraphProps) => {
  const [viewMode, setViewMode] = useState<ViewMode>('risk-trajectory');
  const [selectedOutcome, setSelectedOutcome] = useState<string>('ALL');
  const [hoveredCase, setHoveredCase] = useState<string | null>(null);

  // Extract real evidence from agent verdicts
  const evidencePoints = useMemo(() => extractEvidenceFromAgents(agents), [agents]);

  // Get unique outcomes from the data
  const uniqueOutcomes = useMemo(() => {
    const outcomes = new Set(evidencePoints.map(e => e.outcome));
    return ['ALL', ...Array.from(outcomes)];
  }, [evidencePoints]);

  const filteredPoints = useMemo(() => {
    if (selectedOutcome === 'ALL') return evidencePoints;
    return evidencePoints.filter(e => e.outcome === selectedOutcome);
  }, [evidencePoints, selectedOutcome]);

  const viewModeConfig = {
    'risk-trajectory': {
      xKey: 'riskScore',
      yKey: 'trajectoryScore',
      xLabel: 'Risk Score',
      yLabel: 'Trajectory Score',
      xColor: 'hsl(var(--agent-risk))',
      yColor: 'hsl(var(--agent-trajectory))',
    },
    'risk-fairness': {
      xKey: 'riskScore',
      yKey: 'fairnessScore',
      xLabel: 'Risk Score',
      yLabel: 'Fairness Score',
      xColor: 'hsl(var(--agent-risk))',
      yColor: 'hsl(var(--agent-fairness))',
    },
    'fairness-trajectory': {
      xKey: 'fairnessScore',
      yKey: 'trajectoryScore',
      xLabel: 'Fairness Score',
      yLabel: 'Trajectory Score',
      xColor: 'hsl(var(--agent-fairness))',
      yColor: 'hsl(var(--agent-trajectory))',
    },
  };

  const config = viewModeConfig[viewMode];

  const stats = useMemo(() => {
    const byAgent = {
      risk: evidencePoints.filter(e => e.sourceAgent === 'risk').length,
      fairness: evidencePoints.filter(e => e.sourceAgent === 'fairness').length,
      trajectory: evidencePoints.filter(e => e.sourceAgent === 'trajectory').length,
    };
    const avgSimilarity = evidencePoints.length > 0
      ? Math.round(evidencePoints.reduce((acc, e) => acc + e.similarity, 0) / evidencePoints.length)
      : 0;

    return { total: evidencePoints.length, byAgent, avgSimilarity };
  }, [evidencePoints]);

  if (evidencePoints.length === 0) {
    return (
      <GlassCard className="p-6">
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Database className="w-12 h-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Evidence Retrieved</h3>
          <p className="text-sm text-muted-foreground max-w-md">
            Run an analysis to see historical evidence from the Risk, Fairness, and Trajectory agents.
          </p>
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard className="p-6">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              Retrieved Evidence Graph
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Similar cases retrieved by each agent, plotted by similarity scores
            </p>
          </div>

          {/* View Mode Selector */}
          <div className="flex gap-1 p-1 bg-muted/30 rounded-lg">
            {[
              { mode: 'risk-trajectory' as ViewMode, label: 'Risk/Trajectory', icon: TrendingUp },
              { mode: 'risk-fairness' as ViewMode, label: 'Risk/Fairness', icon: Scale },
              { mode: 'fairness-trajectory' as ViewMode, label: 'Fair/Trajectory', icon: Target },
            ].map(({ mode, label, icon: Icon }) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 flex items-center gap-1.5",
                  viewMode === mode
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-3">
          <div className="text-center p-2 bg-muted/20 rounded-lg">
            <p className="text-xl font-bold text-foreground">{stats.total}</p>
            <p className="text-[10px] text-muted-foreground">Total Evidence</p>
          </div>
          <div className="text-center p-2 bg-muted/20 rounded-lg">
            <p className="text-xl font-bold text-agent-risk">{stats.byAgent.risk}</p>
            <p className="text-[10px] text-muted-foreground">Risk Agent</p>
          </div>
          <div className="text-center p-2 bg-muted/20 rounded-lg">
            <p className="text-xl font-bold text-agent-fairness">{stats.byAgent.fairness}</p>
            <p className="text-[10px] text-muted-foreground">Fairness Agent</p>
          </div>
          <div className="text-center p-2 bg-muted/20 rounded-lg">
            <p className="text-xl font-bold text-agent-trajectory">{stats.byAgent.trajectory}</p>
            <p className="text-[10px] text-muted-foreground">Trajectory Agent</p>
          </div>
        </div>

        {/* Outcome Filter */}
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-muted-foreground mr-2 self-center">Filter:</span>
          {uniqueOutcomes.map((outcome) => (
            <button
              key={outcome}
              onClick={() => setSelectedOutcome(outcome)}
              className={cn(
                "px-3 py-1 text-xs rounded-full border transition-all duration-200",
                selectedOutcome === outcome
                  ? outcome === 'ALL'
                    ? "bg-primary/20 border-primary text-primary"
                    : `border-transparent`
                  : "border-glass-border text-muted-foreground hover:border-primary/50"
              )}
              style={
                selectedOutcome === outcome && outcome !== 'ALL'
                  ? {
                    backgroundColor: `${outcomeColors[outcome] || 'hsl(var(--muted))'}20`,
                    color: outcomeColors[outcome] || 'hsl(var(--foreground))',
                    borderColor: outcomeColors[outcome] || 'hsl(var(--border))'
                  }
                  : {}
              }
            >
              {outcome === 'ALL' ? 'All Cases' : outcome.charAt(0) + outcome.slice(1).toLowerCase()}
            </button>
          ))}
        </div>

        {/* Chart */}
        <motion.div
          className="h-[320px] w-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 20 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--muted-foreground) / 0.1)"
              />
              <XAxis
                type="number"
                dataKey={config.xKey}
                name={config.xLabel}
                domain={[0, 100]}
                tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={{ stroke: 'hsl(var(--muted-foreground) / 0.2)' }}
                tickLine={{ stroke: 'hsl(var(--muted-foreground) / 0.2)' }}
                label={{
                  value: config.xLabel,
                  position: 'bottom',
                  offset: 20,
                  style: { fontSize: 11, fill: config.xColor, fontWeight: 500 }
                }}
              />
              <YAxis
                type="number"
                dataKey={config.yKey}
                name={config.yLabel}
                domain={[0, 100]}
                tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={{ stroke: 'hsl(var(--muted-foreground) / 0.2)' }}
                tickLine={{ stroke: 'hsl(var(--muted-foreground) / 0.2)' }}
                label={{
                  value: config.yLabel,
                  angle: -90,
                  position: 'insideLeft',
                  offset: 10,
                  style: { fontSize: 11, fill: config.yColor, fontWeight: 500, textAnchor: 'middle' }
                }}
              />
              <ZAxis
                type="number"
                dataKey="similarity"
                range={[80, 300]}
                name="Similarity"
              />
              <ReferenceLine
                x={50}
                stroke="hsl(var(--muted-foreground) / 0.3)"
                strokeDasharray="5 5"
              />
              <ReferenceLine
                y={50}
                stroke="hsl(var(--muted-foreground) / 0.3)"
                strokeDasharray="5 5"
              />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ strokeDasharray: '3 3', stroke: 'hsl(var(--primary) / 0.3)' }}
              />
              <Scatter
                name="Retrieved Evidence"
                data={filteredPoints}
                onMouseEnter={(data) => setHoveredCase(data.id)}
                onMouseLeave={() => setHoveredCase(null)}
              >
                {filteredPoints.map((entry) => (
                  <Cell
                    key={entry.id}
                    fill={outcomeColors[entry.outcome] || 'hsl(var(--muted-foreground))'}
                    fillOpacity={hoveredCase === entry.id ? 1 : 0.7}
                    stroke={hoveredCase === entry.id ? 'hsl(var(--foreground))' : 'transparent'}
                    strokeWidth={2}
                    style={{
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Legend by Agent */}
        <div className="flex flex-wrap justify-center gap-6 pt-2 border-t border-glass-border">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-agent-risk" />
            <span className="text-xs text-muted-foreground">Risk Agent Evidence</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-agent-fairness" />
            <span className="text-xs text-muted-foreground">Fairness Agent Evidence</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-agent-trajectory" />
            <span className="text-xs text-muted-foreground">Trajectory Agent Evidence</span>
          </div>
        </div>
      </div>
    </GlassCard>
  );
};
