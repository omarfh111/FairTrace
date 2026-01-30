import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect } from "react";
import { cn } from "@/lib/utils";

interface AnimatedCounterProps {
    value: number;
    duration?: number;
    suffix?: string;
    prefix?: string;
    className?: string;
    decimals?: number;
}

export const AnimatedCounter = ({
    value,
    duration = 1.5,
    suffix = "",
    prefix = "",
    className,
    decimals = 0,
}: AnimatedCounterProps) => {
    const motionValue = useMotionValue(0);
    const rounded = useTransform(motionValue, (v) =>
        decimals > 0 ? v.toFixed(decimals) : Math.round(v).toString()
    );

    useEffect(() => {
        const controls = animate(motionValue, value, {
            duration,
            ease: "easeOut",
        });

        return controls.stop;
    }, [value, duration, motionValue]);

    return (
        <motion.span
            className={cn("tabular-nums", className)}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
        >
            {prefix}
            <motion.span>{rounded}</motion.span>
            {suffix}
        </motion.span>
    );
};
