import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type DecisionType = 'APPROVE' | 'REJECT' | 'CONDITIONAL' | 'ESCALATE';

interface DecisionAuraProps {
    decision: DecisionType;
    className?: string;
    children?: React.ReactNode;
}

const auraConfig: Record<DecisionType, {
    gradient: string;
    pulseColor: string;
    animation: 'aurora' | 'pulse' | 'beacon';
}> = {
    APPROVE: {
        gradient: 'radial-gradient(ellipse at center, hsl(142 71% 45% / 0.2) 0%, hsl(142 71% 45% / 0.05) 40%, transparent 70%)',
        pulseColor: 'hsl(142 71% 45% / 0.3)',
        animation: 'aurora',
    },
    REJECT: {
        gradient: 'radial-gradient(ellipse at center, hsl(0 72% 51% / 0.2) 0%, hsl(0 72% 51% / 0.05) 40%, transparent 70%)',
        pulseColor: 'hsl(0 72% 51% / 0.3)',
        animation: 'pulse',
    },
    CONDITIONAL: {
        gradient: 'radial-gradient(ellipse at center, hsl(38 92% 50% / 0.2) 0%, hsl(38 92% 50% / 0.05) 40%, transparent 70%)',
        pulseColor: 'hsl(38 92% 50% / 0.3)',
        animation: 'beacon',
    },
    ESCALATE: {
        gradient: 'radial-gradient(ellipse at center, hsl(25 95% 53% / 0.2) 0%, hsl(25 95% 53% / 0.05) 40%, transparent 70%)',
        pulseColor: 'hsl(25 95% 53% / 0.3)',
        animation: 'beacon',
    },
};

export const DecisionAura = ({
    decision,
    className,
    children,
}: DecisionAuraProps) => {
    const config = auraConfig[decision];

    return (
        <div className={cn("relative", className)}>
            {/* Main aura gradient */}
            <motion.div
                className="absolute inset-0 pointer-events-none"
                style={{ background: config.gradient }}
                animate={
                    config.animation === 'aurora'
                        ? { opacity: [0.6, 1, 0.6] }
                        : config.animation === 'pulse'
                            ? { scale: [1, 1.02, 1], opacity: [0.7, 1, 0.7] }
                            : { opacity: [0.5, 1, 0.5] }
                }
                transition={{
                    duration: config.animation === 'beacon' ? 2 : 3,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />

            {/* Subtle ring pulse for ESCALATE/CONDITIONAL */}
            {(decision === 'ESCALATE' || decision === 'CONDITIONAL') && (
                <motion.div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        border: `2px solid ${config.pulseColor}`,
                        borderRadius: 'inherit',
                    }}
                    animate={{
                        opacity: [0, 0.5, 0],
                        scale: [0.98, 1.02, 0.98],
                    }}
                    transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: "easeInOut",
                    }}
                />
            )}

            {children}
        </div>
    );
};
