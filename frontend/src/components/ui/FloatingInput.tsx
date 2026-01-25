import { cn } from "@/lib/utils";
import { forwardRef, useState } from "react";

interface FloatingInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export const FloatingInput = forwardRef<HTMLInputElement, FloatingInputProps>(
  ({ label, error, className, value, ...props }, ref) => {
    const [isFocused, setIsFocused] = useState(false);
    const hasValue = value !== undefined && value !== '';

    return (
      <div className="relative">
        <input
          ref={ref}
          value={value}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          className={cn(
            "w-full px-4 pt-6 pb-2 bg-secondary/50 border border-glass-border rounded-lg",
            "text-foreground placeholder-transparent",
            "transition-all duration-300",
            "focus:outline-none focus:border-primary focus:shadow-[0_0_20px_hsl(250_89%_66%/0.15)]",
            "hover:border-muted-foreground/30",
            error && "border-destructive focus:border-destructive",
            className
          )}
          placeholder={label}
          {...props}
        />
        <label
          className={cn(
            "absolute left-4 transition-all duration-200 pointer-events-none",
            "text-muted-foreground",
            isFocused || hasValue
              ? "top-2 text-xs font-medium"
              : "top-1/2 -translate-y-1/2 text-sm",
            isFocused && "text-primary"
          )}
        >
          {label}
        </label>
        {error && (
          <p className="mt-1 text-xs text-destructive">{error}</p>
        )}
      </div>
    );
  }
);

FloatingInput.displayName = "FloatingInput";
