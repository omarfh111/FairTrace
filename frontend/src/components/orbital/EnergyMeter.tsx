import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect, useMemo } from "react";
import { cn } from "@/lib/utils";

interface EnergyMeterProps {
    value: number;
    max?: number;
    color?: 'risk' | 'fairness' | 'trajectory' | 'primary';
    showParticles?: boolean;
    size?: 'sm' | 'md' | 'lg';
    className?: string;
    animated?: boolean;
}

const colorConfig = {
    risk: {
        gradient: 'from-red-600 via-red-500 to-orange-400',
        glow: 'shadow-[0_0_10px_hsl(var(--agent-risk)/0.5)]',
        bg: 'bg-agent-risk/20',
    },
    fairness: {
        gradient: 'from-emerald-600 via-green-500 to-teal-400',
        glow: 'shadow-[0_0_10px_hsl(var(--agent-fairness)/0.5)]',
        bg: 'bg-agent-fairness/20',
    },
    trajectory: {
        gradient: 'from-blue-600 via-blue-500 to-cyan-400',
        glow: 'shadow-[0_0_10px_hsl(var(--agent-trajectory)/0.5)]',
        bg: 'bg-agent-trajectory/20',
    },
    primary: {
        gradient: 'from-purple-600 via-indigo-500 to-blue-400',
        glow: 'shadow-[0_0_10px_hsl(var(--primary)/0.5)]',
        bg: 'bg-primary/20',
    },
};

const sizeConfig = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4',
};

export const EnergyMeter = ({
    value,
    max = 100,
    color = 'primary',
    showParticles = true,
    size = 'md',
    className,
    animated = true,
}: EnergyMeterProps) => {
    const percentage = Math.min((value / max) * 100, 100);
    const config = colorConfig[color];

    // Animated percentage
    const motionValue = useMotionValue(0);
    const displayPercentage = useTransform(motionValue, v => Math.round(v));

    useEffect(() => {
        if (animated) {
            animate(motionValue, percentage, { duration: 1.2, ease: "easeOut" });
        } else {
            motionValue.set(percentage);
        }
    }, [percentage, animated, motionValue]);

    // Generate particle positions
    const particles = useMemo(() => {
        return Array.from({ length: 5 }, (_, i) => ({
            id: i,
            delay: i * 0.3,
        }));
    }, []);

    return (
        <div className={cn("relative w-full", className)}>
            {/* Background track */}
            <div className={cn(
                "w-full rounded-full overflow-hidden relative",
                sizeConfig[size],
                config.bg
            )}>
                {/* Progress bar */}
                <motion.div
                    className={cn(
                        "h-full rounded-full bg-gradient-to-r relative overflow-hidden",
                        config.gradient,
                        config.glow
                    )}
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: animated ? 1.2 : 0, ease: "easeOut" }}
                >
                    {/* Shimmer effect */}
                    <motion.div
                        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                        animate={{ x: ['-100%', '200%'] }}
                        transition={{ duration: 2, repeat: Infinity, ease: "linear", repeatDelay: 1 }}
                    />

                    {/* Particles */}
                    {showParticles && particles.map(particle => (
                        <motion.div
                            key={particle.id}
                            className="absolute w-1 h-1 rounded-full bg-white/80"
                            style={{
                                top: '50%',
                                transform: 'translateY(-50%)',
                            }}
                            animate={{
                                right: ['0%', '100%'],
                                opacity: [0, 1, 0],
                                scale: [0.5, 1, 0.5],
                            }}
                            transition={{
                                duration: 1.5,
                                delay: particle.delay,
                                repeat: Infinity,
                                ease: "easeOut",
                            }}
                        />
                    ))}
                </motion.div>

                {/* Tick marks */}
                <div className="absolute inset-0 flex justify-between px-[25%] items-center pointer-events-none">
                    {[25, 50, 75].map(tick => (
                        <div
                            key={tick}
                            className="w-px h-full bg-white/10"
                            style={{ position: 'absolute', left: `${tick}%` }}
                        />
                    ))}
                </div>
            </div>

            {/* Percentage label */}
            <motion.span
                className="absolute right-0 -top-5 text-xs font-medium text-muted-foreground"
            >
                <motion.span>{displayPercentage}</motion.span>%
            </motion.span>
        </div>
    );
};
