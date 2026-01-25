import { cn } from "@/lib/utils";
import { Decision, Recommendation } from "@/types/application";
import { motion } from "framer-motion";

interface DecisionBadgeProps {
  decision: Decision | Recommendation;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const DecisionBadge = ({ decision, size = 'md', className }: DecisionBadgeProps) => {
  const variants = {
    APPROVE: 'bg-success/20 text-success border-success/30',
    REJECT: 'bg-destructive/20 text-destructive border-destructive/30',
    CONDITIONAL: 'bg-warning/20 text-warning border-warning/30',
    ESCALATE: 'bg-escalate/20 text-escalate border-escalate/30',
    CAUTION: 'bg-warning/20 text-warning border-warning/30',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };

  const icons = {
    APPROVE: '✓',
    REJECT: '✕',
    CONDITIONAL: '⚡',
    ESCALATE: '↑',
    CAUTION: '⚠',
  };

  return (
    <motion.span
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 15 }}
      className={cn(
        "inline-flex items-center gap-1.5 font-semibold rounded-full border",
        variants[decision],
        sizes[size],
        className
      )}
    >
      <span>{icons[decision]}</span>
      {decision}
    </motion.span>
  );
};
