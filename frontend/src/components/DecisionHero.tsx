import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { DecisionResult } from "@/types/application";
import {
    CheckCircle,
    XCircle,
    AlertTriangle,
    ArrowUpRight,
    Clock,
    Zap,
    Users,
    Shield,
    Scale,
    TrendingUp
} from "lucide-react";
import { DecisionAura, AnimatedCounter, AgentSphere, OrbitalRing } from "@/components/orbital";

interface DecisionHeroProps {
    result: DecisionResult;
}

type DecisionType = 'APPROVE' | 'REJECT' | 'CONDITIONAL' | 'ESCALATE';

const decisionConfig: Record<DecisionType, {
    label: string;
    icon: typeof CheckCircle;
    gradient: string;
    borderColor: string;
    iconColor: string;
}> = {
    APPROVE: {
        label: 'Approved',
        icon: CheckCircle,
        gradient: 'from-success/20 via-success/10 to-transparent',
        borderColor: 'border-success/50',
        iconColor: 'text-success',
    },
    REJECT: {
        label: 'Rejected',
        icon: XCircle,
        gradient: 'from-destructive/20 via-destructive/10 to-transparent',
        borderColor: 'border-destructive/50',
        iconColor: 'text-destructive',
    },
    CONDITIONAL: {
        label: 'Conditional',
        icon: AlertTriangle,
        gradient: 'from-warning/20 via-warning/10 to-transparent',
        borderColor: 'border-warning/50',
        iconColor: 'text-warning',
    },
    ESCALATE: {
        label: 'Escalated',
        icon: ArrowUpRight,
        gradient: 'from-escalate/20 via-escalate/10 to-transparent',
        borderColor: 'border-escalate/50',
        iconColor: 'text-escalate',
    },
};

export const DecisionHero = ({ result }: DecisionHeroProps) => {
    const config = decisionConfig[result.decision] || decisionConfig.CONDITIONAL;
    const Icon = config.icon;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            <DecisionAura decision={result.decision}>
                <div className={cn(
                    "relative overflow-hidden rounded-2xl border backdrop-blur-xl",
                    "bg-gradient-to-br",
                    config.gradient,
                    config.borderColor
                )}>
                    {/* Background decorations */}
                    <div className="absolute inset-0 overflow-hidden pointer-events-none">
                        {/* Subtle grid pattern */}
                        <div className="absolute inset-0 bg-grid-pattern opacity-10" />

                        {/* Orbital ring decorations */}
                        <div className="absolute -right-20 -top-20 opacity-20">
                            <OrbitalRing size={200} thickness={1} duration={30} color="hsl(var(--primary) / 0.3)" />
                        </div>
                        <div className="absolute -left-10 -bottom-10 opacity-15">
                            <OrbitalRing size={150} thickness={1} duration={25} reverse color="hsl(var(--primary) / 0.2)" />
                        </div>
                    </div>

                    <div className="relative z-10 p-6 md:p-8">
                        {/* Header with Decision Badge */}
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                            <div className="flex items-center gap-4">
                                {/* Decision Core with glow */}
                                <motion.div
                                    className={cn(
                                        "relative flex items-center justify-center w-16 h-16 rounded-2xl",
                                        "bg-gradient-to-br from-card/80 to-card/60",
                                        "border border-white/10 shadow-lg"
                                    )}
                                    initial={{ scale: 0, rotate: -180 }}
                                    animate={{ scale: 1, rotate: 0 }}
                                    transition={{ type: "spring", stiffness: 200, damping: 15, delay: 0.2 }}
                                >
                                    {/* Pulsing glow ring */}
                                    <motion.div
                                        className={cn("absolute inset-0 rounded-2xl", config.iconColor.replace('text-', 'bg-').concat('/20'))}
                                        animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.2, 0.5] }}
                                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                                    />
                                    <Icon className={cn("w-8 h-8 relative z-10", config.iconColor)} />
                                </motion.div>

                                <div>
                                    <motion.div
                                        className="flex items-center gap-2"
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: 0.3 }}
                                    >
                                        <span className={cn(
                                            "text-2xl md:text-3xl font-bold",
                                            config.iconColor
                                        )}>
                                            {config.label}
                                        </span>
                                    </motion.div>
                                    <motion.p
                                        className="text-sm text-muted-foreground font-mono"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{ delay: 0.5 }}
                                    >
                                        Application #{result.applicationId}
                                    </motion.p>
                                </div>
                            </div>
                        </div>

                        {/* Stats Grid */}
                        <div className="grid grid-cols-3 gap-4 mb-6">
                            {/* Confidence */}
                            <motion.div
                                className="p-4 rounded-xl bg-card/40 border border-white/5"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.4 }}
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    <Zap className="w-4 h-4 text-primary" />
                                    <span className="text-xs text-muted-foreground uppercase tracking-wide">Confidence</span>
                                </div>
                                <AnimatedCounter
                                    value={result.confidence}
                                    suffix="%"
                                    className="text-2xl font-bold text-foreground"
                                    duration={1.5}
                                />
                            </motion.div>

                            {/* Processing Time */}
                            <motion.div
                                className="p-4 rounded-xl bg-card/40 border border-white/5"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.5 }}
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    <Clock className="w-4 h-4 text-agent-trajectory" />
                                    <span className="text-xs text-muted-foreground uppercase tracking-wide">Time</span>
                                </div>
                                <AnimatedCounter
                                    value={result.processingTime}
                                    suffix="s"
                                    className="text-2xl font-bold text-foreground"
                                    decimals={1}
                                    duration={1.5}
                                />
                            </motion.div>

                            {/* Agent Consensus */}
                            <motion.div
                                className="p-4 rounded-xl bg-card/40 border border-white/5"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.6 }}
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    <Users className="w-4 h-4 text-agent-fairness" />
                                    <span className="text-xs text-muted-foreground uppercase tracking-wide">Agents</span>
                                </div>
                                <div className="flex items-center gap-1">
                                    {result.agents.map((agent, i) => (
                                        <motion.div
                                            key={agent.agentName}
                                            initial={{ scale: 0 }}
                                            animate={{ scale: 1 }}
                                            transition={{ delay: 0.8 + i * 0.1, type: "spring" }}
                                            title={`${agent.agentName}: ${agent.recommendation}`}
                                        >
                                            <AgentSphere
                                                agent={agent.agentColor}
                                                size="sm"
                                                showGlow
                                                pulse={agent.recommendation === 'APPROVE'}
                                            />
                                        </motion.div>
                                    ))}
                                </div>
                            </motion.div>
                        </div>

                        {/* Executive Summary */}
                        <motion.div
                            className="p-4 rounded-xl bg-card/30 border border-white/5"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.7 }}
                        >
                            <h3 className="text-sm font-semibold text-muted-foreground mb-2 flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                                Executive Summary
                            </h3>
                            <motion.p
                                className="text-sm text-foreground/90 leading-relaxed"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.9, duration: 0.5 }}
                            >
                                {highlightAgentMentions(result.summary)}
                            </motion.p>
                        </motion.div>
                    </div>
                </div>
            </DecisionAura>
        </motion.div>
    );
};

// Helper to highlight agent mentions in summary text
function highlightAgentMentions(text: string): React.ReactNode {
    const parts = text.split(/(Risk Agent|Fairness Agent|Trajectory Agent)/gi);

    return parts.map((part, i) => {
        const lower = part.toLowerCase();
        if (lower.includes('risk agent')) {
            return <span key={i} className="text-agent-risk font-medium">{part}</span>;
        }
        if (lower.includes('fairness agent')) {
            return <span key={i} className="text-agent-fairness font-medium">{part}</span>;
        }
        if (lower.includes('trajectory agent')) {
            return <span key={i} className="text-agent-trajectory font-medium">{part}</span>;
        }
        return part;
    });
}
