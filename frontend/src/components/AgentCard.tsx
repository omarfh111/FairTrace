import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/ui/GlassCard";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { AgentVerdict } from "@/types/application";
import { ChevronDown, AlertCircle, CheckCircle } from "lucide-react";
import { useState } from "react";

interface AgentCardProps {
  verdict: AgentVerdict;
  index: number;
}

export const AgentCard = ({ verdict, index }: AgentCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const borderColors = {
    risk: 'border-l-destructive',
    fairness: 'border-l-success',
    trajectory: 'border-l-agent-trajectory',
  };

  const iconColors = {
    risk: 'text-destructive',
    fairness: 'text-success',
    trajectory: 'text-agent-trajectory',
  };

  const agentEmojis = {
    risk: '🔴',
    fairness: '🟢',
    trajectory: '🔵',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.15 }}
    >
      <GlassCard
        className={cn(
          "p-5 border-l-4 hover:border-l-[6px] transition-all",
          borderColors[verdict.agentColor]
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center text-lg",
              verdict.agentColor === 'risk' && 'bg-destructive/20',
              verdict.agentColor === 'fairness' && 'bg-success/20',
              verdict.agentColor === 'trajectory' && 'bg-agent-trajectory/20',
            )}>
              {agentEmojis[verdict.agentColor]}
            </div>
            <div>
              <h3 className="font-semibold">{verdict.agentName}</h3>
              <p className={cn("text-xs", iconColors[verdict.agentColor])}>
                {verdict.agentRole}
              </p>
            </div>
          </div>
          <DecisionBadge decision={verdict.recommendation} size="sm" />
        </div>

        {/* Confidence */}
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted-foreground">Confidence</span>
            <span className="font-mono">{verdict.confidence}%</span>
          </div>
          <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
            <motion.div
              className={cn(
                "h-full rounded-full",
                verdict.agentColor === 'risk' && 'bg-destructive',
                verdict.agentColor === 'fairness' && 'bg-success',
                verdict.agentColor === 'trajectory' && 'bg-agent-trajectory',
              )}
              initial={{ width: 0 }}
              animate={{ width: `${verdict.confidence}%` }}
              transition={{ delay: index * 0.15 + 0.3, duration: 0.5 }}
            />
          </div>
        </div>

        {/* Reasoning */}
        <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
          {verdict.reasoning}
        </p>

        {/* Expandable Section */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-xs text-primary hover:text-primary/80 transition-colors mb-3"
        >
          <ChevronDown className={cn(
            "w-4 h-4 transition-transform",
            isExpanded && "rotate-180"
          )} />
          {isExpanded ? 'Hide details' : 'Show details'}
        </button>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="space-y-4 pt-3 border-t border-glass-border overflow-hidden"
            >
              {/* Concerns */}
              {verdict.concerns.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-destructive mb-2 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    Key Concerns
                  </h4>
                  <ul className="space-y-1">
                    {verdict.concerns.map((concern, i) => (
                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                        <span className="text-destructive mt-1">•</span>
                        {concern}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Mitigating Factors */}
              {verdict.mitigatingFactors.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-success mb-2 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    Mitigating Factors
                  </h4>
                  <ul className="space-y-1">
                    {verdict.mitigatingFactors.map((factor, i) => (
                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                        <span className="text-success mt-1">•</span>
                        {factor}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Similar Cases */}
              {verdict.similarCases.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground mb-2">
                    Similar Historical Cases
                  </h4>
                  <div className="space-y-2">
                    {verdict.similarCases.map((caseItem, i) => {
                      // Ensure similarity is a valid number
                      const similarity = typeof caseItem.similarity === 'number' && !isNaN(caseItem.similarity)
                        ? caseItem.similarity
                        : 0;

                      return (
                        <div key={i} className="bg-secondary/50 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-mono text-xs text-primary">{caseItem.entityId || 'Unknown'}</span>
                            <span className={cn(
                              "text-xs px-2 py-0.5 rounded-full",
                              caseItem.outcome === 'APPROVED' && 'bg-success/20 text-success',
                              caseItem.outcome === 'BANKRUPT' && 'bg-destructive/20 text-destructive',
                              caseItem.outcome === 'REJECTED' && 'bg-warning/20 text-warning',
                              caseItem.outcome === 'DEFAULTED' && 'bg-destructive/20 text-destructive',
                              caseItem.outcome === 'FUNDED' && 'bg-success/20 text-success',
                              caseItem.outcome === 'STABLE' && 'bg-success/20 text-success',
                              caseItem.outcome === 'WATCHLIST' && 'bg-warning/20 text-warning',
                              caseItem.outcome === 'DEFAULT' && 'bg-destructive/20 text-destructive',
                            )}>
                              {caseItem.outcome || 'UNKNOWN'}
                            </span>
                          </div>
                          <div className="mb-2">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-muted-foreground">Similarity</span>
                              <span className="font-mono">{similarity}%</span>
                            </div>
                            <div className="h-1 bg-secondary rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full"
                                style={{ width: `${Math.min(100, Math.max(0, similarity))}%` }}
                              />
                            </div>
                          </div>
                          {caseItem.reasoning && (
                            <p className="text-xs text-muted-foreground">{caseItem.reasoning}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </GlassCard>
    </motion.div>
  );
};
