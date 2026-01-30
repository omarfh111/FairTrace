import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/GlassCard";
import { cn } from "@/lib/utils";
import { mockHistoryData } from "@/lib/mockData";
import { Clock, TrendingUp, CheckCircle, XCircle, AlertTriangle, ArrowUpRight, Zap } from "lucide-react";
import { AnimatedCounter } from "@/components/orbital";

export const HistorySidebar = () => {
  const stats = {
    today: 47,
    approvalRate: 68,
    avgTime: 12.3,
  };

  return (
    <div className="space-y-6">
      {/* Quick Stats */}
      <GlassCard className="p-5 relative overflow-hidden" hover={false}>
        {/* Subtle orbital decoration */}
        <motion.div
          className="absolute -right-12 -top-12 w-24 h-24 border border-primary/10 rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        />

        <h3 className="text-sm font-semibold mb-4 text-muted-foreground flex items-center gap-2">
          <Zap className="w-4 h-4 text-primary" />
          Today's Performance
        </h3>
        <div className="grid grid-cols-3 gap-4 relative z-10">
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <AnimatedCounter
              value={stats.today}
              className="text-2xl font-bold block"
              duration={1.2}
            />
            <p className="text-xs text-muted-foreground">Decisions</p>
          </motion.div>
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <AnimatedCounter
              value={stats.approvalRate}
              suffix="%"
              className="text-2xl font-bold text-success block"
              duration={1.2}
            />
            <p className="text-xs text-muted-foreground">Approved</p>
          </motion.div>
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <AnimatedCounter
              value={stats.avgTime}
              suffix="s"
              decimals={1}
              className="text-2xl font-bold block"
              duration={1.2}
            />
            <p className="text-xs text-muted-foreground">Avg Time</p>
          </motion.div>
        </div>
      </GlassCard>

      {/* Trend Chart with glow effect */}
      <GlassCard className="p-5" hover={false}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-muted-foreground">Weekly Trend</h3>
          <motion.div
            animate={{ y: [0, -2, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <TrendingUp className="w-4 h-4 text-success" />
          </motion.div>
        </div>
        <div className="flex items-end justify-between h-16 gap-1">
          {[40, 65, 45, 80, 55, 70, 85].map((height, i) => (
            <motion.div
              key={i}
              initial={{ height: 0 }}
              animate={{ height: `${height}%` }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="flex-1 bg-gradient-to-t from-primary/50 to-primary rounded-t relative overflow-hidden group hover:from-primary/70 hover:to-primary transition-colors cursor-pointer"
              whileHover={{ scaleY: 1.05 }}
            >
              {/* Shimmer effect on hover */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-t from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100"
                initial={{ y: '100%' }}
                whileHover={{ y: '-100%' }}
                transition={{ duration: 0.5 }}
              />
            </motion.div>
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
          <button className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors">
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
              className="flex items-center justify-between py-2 border-b border-glass-border last:border-0 group hover:bg-secondary/20 rounded-lg px-2 -mx-2 transition-colors cursor-pointer"
              whileHover={{ x: 4 }}
            >
              <div className="flex items-center gap-3">
                <motion.div
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center transition-shadow",
                    item.decision === 'APPROVE' && 'bg-success/20 group-hover:shadow-[0_0_10px_hsl(var(--success)/0.3)]',
                    item.decision === 'REJECT' && 'bg-destructive/20 group-hover:shadow-[0_0_10px_hsl(var(--destructive)/0.3)]',
                    item.decision === 'CONDITIONAL' && 'bg-warning/20 group-hover:shadow-[0_0_10px_hsl(var(--warning)/0.3)]',
                    item.decision === 'ESCALATE' && 'bg-escalate/20 group-hover:shadow-[0_0_10px_hsl(var(--escalate)/0.3)]',
                  )}
                >
                  {item.decision === 'APPROVE' && <CheckCircle className="w-4 h-4 text-success" />}
                  {item.decision === 'REJECT' && <XCircle className="w-4 h-4 text-destructive" />}
                  {item.decision === 'CONDITIONAL' && <AlertTriangle className="w-4 h-4 text-warning" />}
                  {item.decision === 'ESCALATE' && <ArrowUpRight className="w-4 h-4 text-escalate" />}
                </motion.div>
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
