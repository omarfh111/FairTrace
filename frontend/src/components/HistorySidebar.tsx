import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/GlassCard";
import { cn } from "@/lib/utils";
import { mockHistoryData } from "@/lib/mockData";
import { Clock, TrendingUp, CheckCircle, XCircle, AlertTriangle, ArrowUpRight } from "lucide-react";

export const HistorySidebar = () => {
  const stats = {
    today: 47,
    approvalRate: 68,
    avgTime: '12.3s',
  };

  return (
    <div className="space-y-6">
      {/* Quick Stats */}
      <GlassCard className="p-5" hover={false}>
        <h3 className="text-sm font-semibold mb-4 text-muted-foreground">Today's Performance</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <span className="text-2xl font-bold">{stats.today}</span>
            <p className="text-xs text-muted-foreground">Decisions</p>
          </div>
          <div className="text-center">
            <span className="text-2xl font-bold text-success">{stats.approvalRate}%</span>
            <p className="text-xs text-muted-foreground">Approved</p>
          </div>
          <div className="text-center">
            <span className="text-2xl font-bold">{stats.avgTime}</span>
            <p className="text-xs text-muted-foreground">Avg Time</p>
          </div>
        </div>
      </GlassCard>

      {/* Trend Chart Placeholder */}
      <GlassCard className="p-5" hover={false}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-muted-foreground">Weekly Trend</h3>
          <TrendingUp className="w-4 h-4 text-success" />
        </div>
        <div className="flex items-end justify-between h-16 gap-1">
          {[40, 65, 45, 80, 55, 70, 85].map((height, i) => (
            <motion.div
              key={i}
              initial={{ height: 0 }}
              animate={{ height: `${height}%` }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="flex-1 bg-gradient-to-t from-primary/50 to-primary rounded-t"
            />
          ))}
        </div>
        <div className="flex justify-between mt-2 text-xs text-muted-foreground">
          <span>Mon</span>
          <span>Tue</span>
          <span>Wed</span>
          <span>Thu</span>
          <span>Fri</span>
          <span>Sat</span>
          <span>Sun</span>
        </div>
      </GlassCard>

      {/* Recent History */}
      <GlassCard className="p-5" hover={false}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-muted-foreground">Recent Decisions</h3>
          <button className="text-xs text-primary hover:text-primary/80 flex items-center gap-1">
            View all <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>
        <div className="space-y-3">
          {mockHistoryData.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className="flex items-center justify-between py-2 border-b border-glass-border last:border-0"
            >
              <div className="flex items-center gap-3">
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center",
                  item.decision === 'APPROVE' && 'bg-success/20',
                  item.decision === 'REJECT' && 'bg-destructive/20',
                  item.decision === 'CONDITIONAL' && 'bg-warning/20',
                  item.decision === 'ESCALATE' && 'bg-escalate/20',
                )}>
                  {item.decision === 'APPROVE' && <CheckCircle className="w-4 h-4 text-success" />}
                  {item.decision === 'REJECT' && <XCircle className="w-4 h-4 text-destructive" />}
                  {item.decision === 'CONDITIONAL' && <AlertTriangle className="w-4 h-4 text-warning" />}
                  {item.decision === 'ESCALATE' && <ArrowUpRight className="w-4 h-4 text-escalate" />}
                </div>
                <div>
                  <p className="text-sm font-medium truncate max-w-[120px]">{item.entity}</p>
                  <p className="text-xs text-muted-foreground">{item.date}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="w-3 h-3" />
                {item.time}
              </div>
            </motion.div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
};
