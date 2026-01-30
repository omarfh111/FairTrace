import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface OrbitalRingProps {
    size?: number;
    thickness?: number;
    color?: string;
    duration?: number;
    reverse?: boolean;
    className?: string;
    children?: React.ReactNode;
}

export const OrbitalRing = ({
    size = 100,
    thickness = 2,
    color = "hsl(var(--primary) / 0.3)",
    duration = 20,
    reverse = false,
    className,
    children,
}: OrbitalRingProps) => {
    return (
        <div className={cn("relative", className)} style={{ width: size, height: size }}>
            <motion.div
                className="absolute inset-0 rounded-full pointer-events-none"
                style={{
                    border: `${thickness}px solid ${color}`,
                }}
                animate={{ rotate: reverse ? -360 : 360 }}
                transition={{
                    duration,
                    repeat: Infinity,
                    ease: "linear",
                }}
            />
            {children && (
                <div className="absolute inset-0 flex items-center justify-center">
                    {children}
                </div>
            )}
        </div>
    );
};
