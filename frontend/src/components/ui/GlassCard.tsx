import { cn } from "@/lib/utils";
import { motion, HTMLMotionProps } from "framer-motion";
import React from "react";

interface GlassCardProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  className?: string;
  glow?: 'primary' | 'success' | 'danger' | 'none';
  hover?: boolean;
}

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ children, className, glow = 'none', hover = true, ...props }, ref) => {
    const glowClasses = {
      primary: 'hover:shadow-[0_0_40px_hsl(250_89%_66%/0.2)]',
      success: 'hover:shadow-[0_0_40px_hsl(142_71%_45%/0.2)]',
      danger: 'hover:shadow-[0_0_40px_hsl(0_72%_51%/0.2)]',
      none: '',
    };

    return (
      <motion.div
        ref={ref}
        className={cn(
          "bg-card/60 backdrop-blur-xl border border-glass-border rounded-xl",
          "transition-all duration-300",
          hover && "hover:border-primary/30 hover:scale-[1.01]",
          glowClasses[glow],
          className
        )}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

GlassCard.displayName = "GlassCard";
