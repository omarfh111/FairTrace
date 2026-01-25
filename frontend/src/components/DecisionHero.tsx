import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { DecisionResult } from "@/types/application";
import { Clock, Shield, TrendingUp } from "lucide-react";

interface DecisionHeroProps {
  result: DecisionResult;
}

export const DecisionHero = ({ result }: DecisionHeroProps) => {
  const gradients = {
    APPROVE: 'from-success/20 via-success/5 to-transparent',
    REJECT: 'from-destructive/20 via-destructive/5 to-transparent',
    CONDITIONAL: 'from-warning/20 via-warning/5 to-transparent',
    ESCALATE: 'from-escalate/20 via-escalate/5 to-transparent',
  };

  const borderColors = {
    APPROVE: 'border-success/30',
    REJECT: 'border-destructive/30',
    CONDITIONAL: 'border-warning/30',
    ESCALATE: 'border-escalate/30',
  };

  const textColors = {
    APPROVE: 'text-success',
    REJECT: 'text-destructive',
    CONDITIONAL: 'text-warning',
    ESCALATE: 'text-escalate',
  };

  const icons = {
    APPROVE: '✅',
    REJECT: '❌',
    CONDITIONAL: '⚡',
    ESCALATE: '🔺',
  };

  const labels = {
    APPROVE: 'Application Approved',
    REJECT: 'Application Declined',
    CONDITIONAL: 'Conditional Approval',
    ESCALATE: 'Escalated for Review',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className={cn(
        "relative overflow-hidden rounded-2xl border backdrop-blur-xl p-8",
        `bg-gradient-to-br ${gradients[result.decision]}`,
        borderColors[result.decision]
      )}
    >
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-grid-pattern opacity-30" />
      
      <div className="relative z-10">
        {/* Main Decision */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-6">
          <div className="flex items-center gap-4">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 300, delay: 0.2 }}
              className="text-6xl"
            >
              {icons[result.decision]}
            </motion.div>
            <div>
              <motion.h1
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className={cn("text-3xl font-bold", textColors[result.decision])}
              >
                {labels[result.decision]}
              </motion.h1>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="text-sm font-mono text-muted-foreground"
              >
                {result.applicationId}
              </motion.p>
            </div>
          </div>

          {/* Stats */}
          <div className="flex gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="text-center"
            >
              <div className="flex items-center gap-1 text-muted-foreground mb-1">
                <Shield className="w-4 h-4" />
                <span className="text-xs">Confidence</span>
              </div>
              <span className="text-2xl font-bold">{result.confidence}%</span>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="text-center"
            >
              <div className="flex items-center gap-1 text-muted-foreground mb-1">
                <Clock className="w-4 h-4" />
                <span className="text-xs">Processing</span>
              </div>
              <span className="text-2xl font-bold">{result.processingTime}s</span>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="text-center"
            >
              <div className="flex items-center gap-1 text-muted-foreground mb-1">
                <TrendingUp className="w-4 h-4" />
                <span className="text-xs">Agents</span>
              </div>
              <span className="text-2xl font-bold">3/3</span>
            </motion.div>
          </div>
        </div>

        {/* Summary */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="text-muted-foreground leading-relaxed"
        >
          {result.summary}
        </motion.p>

        {/* Agent Agreement Indicator */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="mt-6 flex items-center gap-4"
        >
          <span className="text-xs text-muted-foreground">Agent Consensus:</span>
          <div className="flex gap-2">
            {result.agents.map((agent, i) => (
              <div
                key={i}
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-sm",
                  agent.recommendation === 'APPROVE' && 'bg-success/20 text-success',
                  agent.recommendation === 'REJECT' && 'bg-destructive/20 text-destructive',
                  agent.recommendation === 'CONDITIONAL' && 'bg-warning/20 text-warning',
                  agent.recommendation === 'CAUTION' && 'bg-warning/20 text-warning',
                )}
                title={`${agent.agentName}: ${agent.recommendation}`}
              >
                {agent.agentColor === 'risk' && '🔴'}
                {agent.agentColor === 'fairness' && '🟢'}
                {agent.agentColor === 'trajectory' && '🔵'}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
};
