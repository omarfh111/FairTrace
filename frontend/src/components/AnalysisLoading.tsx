
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useMemo, useEffect, useState } from "react";

const agents = [
  {
    name: 'Risk Agent',
    role: 'The Prosecutor',
    color: 'bg-destructive',
    shadowColor: 'shadow-destructive/50',
    gradientFrom: '#ef4444',
    icon: '🛡️'
  },
  {
    name: 'Fairness Agent',
    role: 'The Advocate',
    color: 'bg-success',
    shadowColor: 'shadow-success/50',
    gradientFrom: '#10b981',
    icon: '⚖️'
  },
  {
    name: 'Trajectory Agent',
    role: 'The Predictor',
    color: 'bg-agent-trajectory',
    shadowColor: 'shadow-agent-trajectory/50',
    gradientFrom: '#3b82f6',
    icon: '📈'
  },
];

interface AnalysisLoadingProps {
  currentAgent: number;
  progress: number;
}

const getOrchestratorMessage = (progress: number, currentAgent: number) => {
  if (progress < 25) return { main: "Risk Agent analyzing...", sub: "Evaluating risk factors and historical patterns" };
  if (progress < 50) return { main: "Fairness Agent analyzing...", sub: "Ensuring equitable treatment standards" };
  if (progress < 75) return { main: "Trajectory Agent analyzing...", sub: "Predicting future trajectory and outcomes" };
  if (progress < 80) return { main: "Orchestrator initializing...", sub: "Preparing to synthesize agent verdicts" };
  if (progress < 85) return { main: "Receiving verdicts...", sub: `Agent data flowing to orchestrator` };
  if (progress < 90) return { main: "Analyzing consensus...", sub: "Comparing agent recommendations" };
  if (progress < 95) return { main: "Synthesizing decision...", sub: "Applying decision logic" };
  if (progress < 100) return { main: "Finalizing...", sub: "Preparing decision summary" };
  return { main: "✓ Decision ready", sub: "Analysis complete" };
};

const getProgressPhase = (progress: number): 'agents' | 'receiving' | 'synthesis' | 'complete' => {
  if (progress < 75) return 'agents';
  if (progress < 85) return 'receiving';
  if (progress < 95) return 'synthesis';
  return 'complete';
};

export const AnalysisLoading = ({ currentAgent, progress }: AnalysisLoadingProps) => {
  const phase = getProgressPhase(progress);
  const message = getOrchestratorMessage(progress, currentAgent);
  const [pulse, setPulse] = useState(0);

  // Periodic pulse effect
  useEffect(() => {
    const interval = setInterval(() => {
      setPulse(p => p + 1);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 bg-black/20 backdrop-blur-sm rounded-xl border border-white/5 relative overflow-hidden">

      {/* Background ambient glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary/10 rounded-full blur-[100px]"
          animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      {/* Main Visualization Area */}
      <div className="relative mb-12 w-full max-w-md h-80 flex items-center justify-center perspective-[1000px]">

        {/* Central Core - The Orchestrator */}
        <div className="relative z-10 w-24 h-24 flex items-center justify-center">
          {/* Shockwaves */}
          {[1, 2, 3].map(i => (
            <motion.div
              key={i}
              className="absolute inset-0 rounded-full border border-primary/30"
              initial={{ scale: 1, opacity: 0.5 }}
              animate={{ scale: 2.5, opacity: 0 }}
              transition={{
                duration: 2,
                repeat: Infinity,
                delay: i * 0.6,
                ease: "easeOut"
              }}
            />
          ))}

          {/* Core Shape */}
          <motion.div
            className="w-full h-full rounded-2xl bg-gradient-to-br from-primary via-indigo-600 to-purple-600 flex items-center justify-center shadow-[0_0_50px_rgba(79,70,229,0.5)] border border-white/20 relative overflow-hidden"
            animate={{
              rotate: phase === 'receiving' ? 180 : 45,
              borderRadius: phase === 'synthesis' ? "50%" : "20%"
            }}
            transition={{ duration: 1.5, ease: "easeInOut" }}
          >
            {/* Inner Energy */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-t from-transparent via-white/10 to-transparent"
              animate={{ y: [-100, 100] }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            />

            <AnimatePresence mode="wait">
              <motion.div
                key={phase}
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.5, opacity: 0 }}
                className="text-4xl"
              >
                {phase === 'complete' ? '✓' : '🧠'}
              </motion.div>
            </AnimatePresence>
          </motion.div>
        </div>

        {/* Orbiting Agents */}
        <div className="absolute inset-0 pointer-events-none">
          {agents.map((agent, index) => {
            const isActive = index === currentAgent && phase === 'agents';
            const hasCompleted = index < currentAgent || phase !== 'agents';
            const isSending = phase === 'receiving';

            // Calculate orbit position
            // We fake 3D orbit using elliptical math and scaling
            const angleOffset = (index * (360 / agents.length));

            return (
              <motion.div
                key={agent.name}
                className="absolute top-1/2 left-1/2 w-16 h-16 -ml-8 -mt-8 flex items-center justify-center"
                animate={phase === 'agents' ? {
                  rotate: [angleOffset, angleOffset + 360],
                  x: [Math.cos((angleOffset * Math.PI) / 180) * 120, Math.cos(((angleOffset + 360) * Math.PI) / 180) * 120],
                  y: [Math.sin((angleOffset * Math.PI) / 180) * 40, Math.sin(((angleOffset + 360) * Math.PI) / 180) * 40], // Ellipse
                  scale: [
                    0.8 + 0.2 * Math.sin((angleOffset * Math.PI) / 180),
                    0.8 + 0.2 * Math.sin(((angleOffset + 360) * Math.PI) / 180)
                  ],
                  zIndex: [
                    Math.sin((angleOffset * Math.PI) / 180) > 0 ? 20 : 0,
                    Math.sin(((angleOffset + 360) * Math.PI) / 180) > 0 ? 20 : 0
                  ]
                } : {
                  // When not orbiting (e.g. synthesis), move to fixed positions
                  rotate: 0,
                  x: Math.cos(((index * 120 - 90) * Math.PI) / 180) * 120,
                  y: Math.sin(((index * 120 - 90) * Math.PI) / 180) * 120,
                  scale: 1,
                  zIndex: 10
                }}
                transition={phase === 'agents' ? {
                  duration: 10,
                  repeat: Infinity,
                  ease: "linear",
                  times: [0, 1] // Ensure smooth loop
                } : {
                  duration: 0.8,
                  ease: "easeInOut"
                }}
              >
                {/* Connecting Line to Center (only when sending) */}
                {isSending && (
                  <motion.div
                    className="absolute top-1/2 left-1/2 h-[2px] bg-gradient-to-r from-transparent via-white w-0 origin-left"
                    style={{
                      width: 120,
                      rotate: `${(Math.atan2(-Math.sin(((index * 120 - 90) * Math.PI) / 180), -Math.cos(((index * 120 - 90) * Math.PI) / 180)) * 180 / Math.PI)}deg`
                    }}
                    initial={{ opacity: 0, scaleX: 0 }}
                    animate={{ opacity: 1, scaleX: 1 }}
                    exit={{ opacity: 0 }}
                  />
                )}

                <div className={cn(
                  "w-12 h-12 rounded-full flex items-center justify-center text-xl shadow-lg border border-white/10 transition-all duration-300 relative",
                  agent.color,
                  isActive && `ring-4 ring-offset-2 ring-offset-black/50 ${agent.shadowColor} scale-110`,
                  hasCompleted && !isActive && "opacity-80 scale-90 grayscale-[0.3]"
                )}>
                  {hasCompleted ? '✓' : agent.icon}
                  {isActive && (
                    <motion.div
                      className="absolute inset-0 rounded-full border-2 border-white"
                      animate={{ scale: [1, 1.5], opacity: [1, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    />
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Status Text Area */}
      <motion.div
        key={message.main}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="text-center mb-8 relative z-20"
      >
        <h3 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white via-white to-white/70 mb-2">
          {message.main}
        </h3>
        <p className="text-blue-200/60 font-medium tracking-wide text-sm">{message.sub}</p>
      </motion.div>

      {/* Advanced Scanner Progress Bar */}
      <div className="w-full max-w-sm mb-8 relative group">
        {/* Glow underlay */}
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full opacity-20 blur-md group-hover:opacity-40 transition-opacity" />

        <div className="h-2 bg-gray-800 rounded-full overflow-hidden relative">
          {/* Fill */}
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.2, ease: "linear" }}
          />
          {/* Scanner Light */}
          <motion.div
            className="absolute top-0 bottom-0 w-24 bg-gradient-to-r from-transparent via-white/80 to-transparent blur-[2px]"
            animate={{ x: ['-100%', '500%'] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
          />
        </div>

        <div className="flex justify-between mt-2 text-[10px] font-mono text-white/30 uppercase tracking-widest">
          <span>Initialization</span>
          <span>Synthesis</span>
          <span>Completion</span>
        </div>
      </div>

      {/* Bottom Pipeline Stages */}
      <div className="flex items-center gap-4 relative z-20">
        {/* Agents Step */}
        <div className="flex items-center gap-2">
          <motion.div
            className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center border transition-colors",
              phase === 'agents' ? "border-primary bg-primary/20 text-blue-300" :
                progress > 0 ? "border-primary/50 bg-primary/10 text-primary" : "border-white/10 text-white/20"
            )}
            animate={phase === 'agents' ? { boxShadow: "0 0 15px rgba(59, 130, 246, 0.5)" } : {}}
          >
            ⚡
          </motion.div>
          <div className={cn("h-[2px] w-8 rounded-full", progress > 50 ? "bg-primary" : "bg-white/10")} />
        </div>

        {/* Synthesis Step */}
        <div className="flex items-center gap-2">
          <motion.div
            className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center border transition-colors",
              phase === 'synthesis' ? "border-purple-500 bg-purple-500/20 text-purple-300" :
                progress > 85 ? "border-purple-500/50 bg-purple-500/10 text-purple-500" : "border-white/10 text-white/20"
            )}
            animate={phase === 'synthesis' ? { boxShadow: "0 0 15px rgba(168, 85, 247, 0.5)" } : {}}
          >
            🔄
          </motion.div>
          <div className={cn("h-[2px] w-8 rounded-full", progress > 95 ? "bg-purple-500" : "bg-white/10")} />
        </div>

        {/* Completion Step */}
        <div className="flex items-center gap-2">
          <motion.div
            className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center border transition-colors",
              phase === 'complete' ? "border-green-500 bg-green-500/20 text-green-300" : "border-white/10 text-white/20"
            )}
            animate={phase === 'complete' ? { scale: [1, 1.2, 1], boxShadow: "0 0 15px rgba(34, 197, 94, 0.5)" } : {}}
          >
            ✓
          </motion.div>
        </div>
      </div>
    </div>
  );
};

