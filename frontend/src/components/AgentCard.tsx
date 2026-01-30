import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/ui/GlassCard";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { AgentVerdict } from "@/types/application";
import { ChevronDown, AlertCircle, CheckCircle, Shield, Scale, TrendingUp } from "lucide-react";
import { useState } from "react";
import { AgentSphere, EnergyMeter } from "@/components/orbital";

interface AgentCardProps {
  verdict: AgentVerdict;
  index: number;
}

const agentIcons = {
  risk: Shield,
  fairness: Scale,
  trajectory: TrendingUp,
};

export const AgentCard = ({ verdict, index }: AgentCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const glowColors = {
    risk: 'shadow-[0_0_30px_hsl(var(--agent-risk)/0.2)]',
    fairness: 'shadow-[0_0_30px_hsl(var(--agent-fairness)/0.2)]',
    trajectory: 'shadow-[0_0_30px_hsl(var(--agent-trajectory)/0.2)]',
  };

  const borderGradients = {
    risk: 'before:bg-gradient-to-b before:from-agent-risk before:to-transparent',
    fairness: 'before:bg-gradient-to-b before:from-agent-fairness before:to-transparent',
    trajectory: 'before:bg-gradient-to-b before:from-agent-trajectory before:to-transparent',
  };

  const iconColors = {
    risk: 'text-destructive',
    fairness: 'text-success',
    trajectory: 'text-agent-trajectory',
  };

  const Icon = agentIcons[verdict.agentColor];

  return (
    <motion.div
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        delay: 0.2 + index * 0.15,
        duration: 0.5,
        ease: [0.25, 0.46, 0.45, 0.94]
      }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
    >
      <div className={cn(
        "relative rounded-xl overflow-hidden",
        "before:absolute before:left-0 before:top-0 before:bottom-0 before:w-1",
        borderGradients[verdict.agentColor]
      )}>
        <GlassCard
          className={cn(
            "p-5 transition-all duration-300 hover:bg-card/70",
            glowColors[verdict.agentColor]
          )}
        >
          {/* Subtle orbital ring decoration */}
          <div className="absolute -right-16 -top-16 w-32 h-32 opacity-10 pointer-events-none">
            <motion.div
              className={cn(
                "w-full h-full rounded-full border-2",
                verdict.agentColor === 'risk' && 'border-agent-risk',
                verdict.agentColor === 'fairness' && 'border-agent-fairness',
                verdict.agentColor === 'trajectory' && 'border-agent-trajectory',
              )}
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            />
          </div>

          {/* Header */}
          <div className="flex items-start justify-between mb-4 relative z-10">
            <div className="flex items-center gap-3">
              <motion.div
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ delay: 0.3 + index * 0.15, type: "spring", stiffness: 200 }}
              >
                <AgentSphere
                  agent={verdict.agentColor}
                  size="md"
                  showGlow
                  icon={<Icon className="w-5 h-5" />}
                />
              </motion.div>
              <div>
                <h3 className="font-semibold text-foreground">{verdict.agentName}</h3>
                <p className={cn("text-xs", iconColors[verdict.agentColor])}>
                  {verdict.agentRole}
                </p>
              </div>
            </div>
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 + index * 0.15 }}
            >
              <DecisionBadge decision={verdict.recommendation} size="sm" />
            </motion.div>
          </div>

          {/* Confidence - Using EnergyMeter */}
          <div className="mb-4 relative z-10">
            <div className="flex justify-between text-xs mb-2">
              <span className="text-muted-foreground">Confidence Level</span>
            </div>
            <EnergyMeter
              value={verdict.confidence}
              color={verdict.agentColor}
              size="md"
              showParticles
              animated
            />
          </div>

          {/* Reasoning */}
          <motion.p
            className="text-sm text-muted-foreground mb-4 leading-relaxed relative z-10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 + index * 0.15 }}
          >
            {verdict.reasoning}
          </motion.p>

          {/* Expandable Section */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={cn(
              "flex items-center gap-2 text-xs transition-all duration-200 mb-3 relative z-10",
              "hover:text-foreground",
              iconColors[verdict.agentColor]
            )}
          >
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="w-4 h-4" />
            </motion.div>
            {isExpanded ? 'Hide details' : 'Show details'}
          </button>

          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="space-y-4 pt-3 border-t border-glass-border overflow-hidden relative z-10"
              >
                {/* Concerns */}
                {verdict.concerns.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    <h4 className="text-xs font-semibold text-destructive mb-2 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      Key Concerns
                    </h4>
                    <ul className="space-y-1">
                      {verdict.concerns.map((concern, i) => (
                        <motion.li
                          key={i}
                          className="text-xs text-muted-foreground flex items-start gap-2"
                          initial={{ opacity: 0, x: -5 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.15 + i * 0.05 }}
                        >
                          <span className="text-destructive mt-1">•</span>
                          {concern}
                        </motion.li>
                      ))}
                    </ul>
                  </motion.div>
                )}

                {/* Mitigating Factors */}
                {verdict.mitigatingFactors.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    <h4 className="text-xs font-semibold text-success mb-2 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      Mitigating Factors
                    </h4>
                    <ul className="space-y-1">
                      {verdict.mitigatingFactors.map((factor, i) => (
                        <motion.li
                          key={i}
                          className="text-xs text-muted-foreground flex items-start gap-2"
                          initial={{ opacity: 0, x: -5 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.25 + i * 0.05 }}
                        >
                          <span className="text-success mt-1">•</span>
                          {factor}
                        </motion.li>
                      ))}
                    </ul>
                  </motion.div>
                )}

                {/* Similar Cases */}
                {verdict.similarCases.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                  >
                    <h4 className="text-xs font-semibold text-muted-foreground mb-2">
                      Similar Historical Cases
                    </h4>
                    <div className="space-y-2">
                      {verdict.similarCases.map((caseItem, i) => {
                        const similarity = typeof caseItem.similarity === 'number' && !isNaN(caseItem.similarity)
                          ? caseItem.similarity
                          : 0;

                        return (
                          <motion.div
                            key={i}
                            className="bg-secondary/50 rounded-lg p-3 border border-white/5"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.35 + i * 0.1 }}
                          >
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
                                <motion.div
                                  className="h-full bg-primary rounded-full"
                                  initial={{ width: 0 }}
                                  animate={{ width: `${Math.min(100, Math.max(0, similarity))}%` }}
                                  transition={{ delay: 0.4, duration: 0.5 }}
                                />
                              </div>
                            </div>
                            {caseItem.reasoning && (
                              <p className="text-xs text-muted-foreground">{caseItem.reasoning}</p>
                            )}
                          </motion.div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </GlassCard>
      </div>
    </motion.div>
  );
};
