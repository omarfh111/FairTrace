import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface AgentSphereProps {
    agent: 'risk' | 'fairness' | 'trajectory';
    size?: 'sm' | 'md' | 'lg';
    showGlow?: boolean;
    pulse?: boolean;
    className?: string;
    icon?: React.ReactNode;
}

const agentConfig = {
    risk: {
        color: 'bg-agent-risk',
        glow: 'shadow-[0_0_20px_hsl(var(--agent-risk)/0.5)]',
        label: 'Risk',
    },
    fairness: {
        color: 'bg-agent-fairness',
        glow: 'shadow-[0_0_20px_hsl(var(--agent-fairness)/0.5)]',
        label: 'Fairness',
    },
    trajectory: {
        color: 'bg-agent-trajectory',
        glow: 'shadow-[0_0_20px_hsl(var(--agent-trajectory)/0.5)]',
        label: 'Trajectory',
    },
};

const sizeConfig = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-14 h-14',
};

export const AgentSphere = ({
    agent,
    size = 'md',
    showGlow = true,
    pulse = false,
    className,
    icon,
}: AgentSphereProps) => {
    const config = agentConfig[agent];

    return (
        <motion.div
            className={cn(
                "rounded-full flex items-center justify-center relative",
                sizeConfig[size],
                config.color,
                showGlow && config.glow,
                className
            )}
            animate={pulse ? { scale: [1, 1.1, 1] } : {}}
            transition={pulse ? { duration: 2, repeat: Infinity, ease: "easeInOut" } : {}}
        >
            {pulse && (
                <motion.div
                    className={cn("absolute inset-0 rounded-full", config.color)}
                    animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "easeOut" }}
                />
            )}
            {icon && (
                <span className="relative z-10 text-white">{icon}</span>
            )}
        </motion.div>
    );
};
