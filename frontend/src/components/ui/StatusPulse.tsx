import { cn } from "@/lib/utils";

interface StatusPulseProps {
  status: 'connected' | 'processing' | 'error';
  label?: string;
  className?: string;
}

export const StatusPulse = ({ status, label, className }: StatusPulseProps) => {
  const colors = {
    connected: 'bg-success',
    processing: 'bg-primary',
    error: 'bg-destructive',
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="relative">
        <div className={cn("w-2 h-2 rounded-full", colors[status])} />
        <div
          className={cn(
            "absolute inset-0 w-2 h-2 rounded-full animate-ping",
            colors[status],
            "opacity-75"
          )}
        />
      </div>
      {label && (
        <span className="text-xs text-muted-foreground font-medium">{label}</span>
      )}
    </div>
  );
};
