import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useMemo } from "react";

const agents = [
  {
    name: 'Risk Agent',
    role: 'The Prosecutor',
    color: 'bg-destructive',
    glowColor: 'shadow-[0_0_40px_hsl(0_72%_51%/0.5)]',
    gradientFrom: '#ef4444',
    icon: '🔴'
  },
  {
    name: 'Fairness Agent',
    role: 'The Advocate',
    color: 'bg-success',
    glowColor: 'shadow-[0_0_40px_hsl(142_71%_45%/0.5)]',
    gradientFrom: '#10b981',
    icon: '🟢'
  },
  {
    name: 'Trajectory Agent',
    role: 'The Predictor',
    color: 'bg-agent-trajectory',
    glowColor: 'shadow-[0_0_40px_hsl(217_91%_60%/0.5)]',
    gradientFrom: '#3b82f6',
    icon: '🔵'
  },
];

interface AnalysisLoadingProps {
  currentAgent: number;
  progress: number;
}

// Get orchestrator messages based on progress
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

// Get progress phase
const getProgressPhase = (progress: number): 'agents' | 'receiving' | 'synthesis' | 'complete' => {
  if (progress < 75) return 'agents';
  if (progress < 85) return 'receiving';
  if (progress < 95) return 'synthesis';
  return 'complete';
};

export const AnalysisLoading = ({ currentAgent, progress }: AnalysisLoadingProps) => {
  const phase = getProgressPhase(progress);
  const message = getOrchestratorMessage(progress, currentAgent);

  // Orchestrator activity level (0-1)
  const orchestratorActivity = useMemo(() => {
    if (progress < 75) return 0.3;
    if (progress < 85) return 0.5 + (progress - 75) * 0.05;
    if (progress < 95) return 1;
    return 0.8;
  }, [progress]);

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      {/* Main Visualization Area */}
      <div className="relative mb-8">
        {/* Background Glow */}
        <motion.div
          className="absolute inset-0 blur-3xl opacity-30"
          style={{
            background: `radial-gradient(circle at center, rgba(139, 92, 246, ${orchestratorActivity * 0.3}) 0%, transparent 70%)`,
          }}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        />

        {/* Central Orchestrator */}
        <div className="relative w-72 h-72 flex items-center justify-center">
          {/* Orchestrator Core */}
          <motion.div
            className="absolute z-20"
            animate={{
              rotate: 360,
            }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          >
            <motion.div
              className="w-24 h-24 rounded-2xl flex items-center justify-center relative"
              style={{
                background: 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 50%, #8b5cf6 100%)',
                boxShadow: phase === 'synthesis' || phase === 'complete'
                  ? '0 0 60px rgba(139, 92, 246, 0.8), inset 0 0 30px rgba(255,255,255,0.2)'
                  : '0 0 30px rgba(139, 92, 246, 0.4)',
              }}
              animate={{
                scale: phase === 'synthesis' ? [1, 1.1, 1] : [1, 1.05, 1],
                boxShadow: phase === 'synthesis'
                  ? [
                    '0 0 30px rgba(139, 92, 246, 0.4)',
                    '0 0 80px rgba(139, 92, 246, 0.8)',
                    '0 0 30px rgba(139, 92, 246, 0.4)',
                  ]
                  : undefined,
              }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            >
              {/* Inner wireframe effect */}
              <div className="absolute inset-2 border border-white/20 rounded-xl" />
              <div className="absolute inset-4 border border-white/10 rounded-lg" />

              {/* Orchestrator Icon */}
              <motion.span
                className="text-4xl z-10"
                animate={{
                  scale: phase === 'complete' ? [1, 1.2, 1] : 1,
                }}
                transition={{ duration: 0.5 }}
              >
                {phase === 'complete' ? '✓' : '🧠'}
              </motion.span>

              {/* Particle effects inside orchestrator */}
              {phase === 'synthesis' && (
                <div className="absolute inset-0 overflow-hidden rounded-2xl">
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={i}
                      className="absolute w-2 h-2 rounded-full"
                      style={{
                        background: agents[i].gradientFrom,
                        left: '50%',
                        top: '50%',
                      }}
                      animate={{
                        x: [0, 20, -20, 10, -10, 0],
                        y: [0, -10, 15, -20, 5, 0],
                        scale: [0.5, 1, 0.8, 1.2, 0.6, 0.5],
                        opacity: [0.8, 1, 0.8, 1, 0.8, 0.8],
                      }}
                      transition={{
                        duration: 2,
                        repeat: Infinity,
                        delay: i * 0.3,
                        ease: "easeInOut",
                      }}
                    />
                  ))}
                </div>
              )}
            </motion.div>
          </motion.div>

          {/* Agent Orbs */}
          {agents.map((agent, index) => {
            const angle = (index * 120 - 90) * (Math.PI / 180);
            const radius = 100;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            const isActive = index === currentAgent && progress < 75;
            const hasCompleted = currentAgent > index || progress >= 75;
            const isSending = phase === 'receiving' && index <= Math.floor((progress - 75) / 3.33);

            return (
              <motion.div
                key={agent.name}
                className="absolute top-1/2 left-1/2"
                style={{
                  x: x - 28,
                  y: y - 28,
                }}
              >
                {/* Data flow line to orchestrator */}
                <AnimatePresence>
                  {(isActive || isSending) && (
                    <svg
                      className="absolute pointer-events-none"
                      style={{
                        width: radius,
                        height: 4,
                        left: 28,
                        top: 26,
                        transform: `rotate(${(index * 120 + 90)}deg)`,
                        transformOrigin: '0 50%',
                      }}
                    >
                      <defs>
                        <linearGradient id={`flow-${index}`} x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor={agent.gradientFrom} stopOpacity="0.8" />
                          <stop offset="50%" stopColor="white" stopOpacity="0.6" />
                          <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.8" />
                        </linearGradient>
                      </defs>
                      <motion.line
                        x1="0"
                        y1="2"
                        x2={radius - 45}
                        y2="2"
                        stroke={`url(#flow-${index})`}
                        strokeWidth="2"
                        strokeDasharray="8 4"
                        initial={{ strokeDashoffset: 40, opacity: 0 }}
                        animate={{
                          strokeDashoffset: [40, 0],
                          opacity: 1,
                        }}
                        exit={{ opacity: 0 }}
                        transition={{
                          strokeDashoffset: { duration: 1, repeat: Infinity, ease: "linear" },
                          opacity: { duration: 0.3 },
                        }}
                      />
                    </svg>
                  )}
                </AnimatePresence>

                {/* Data particles flowing to center */}
                {isSending && (
                  <>
                    {[0, 1, 2].map((pi) => (
                      <motion.div
                        key={pi}
                        className="absolute w-2 h-2 rounded-full"
                        style={{
                          background: agent.gradientFrom,
                          left: 24,
                          top: 24,
                        }}
                        initial={{
                          x: 0,
                          y: 0,
                          scale: 1,
                          opacity: 1,
                        }}
                        animate={{
                          x: -x + 12,
                          y: -y + 12,
                          scale: [1, 1.5, 0.5],
                          opacity: [1, 1, 0],
                        }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          delay: pi * 0.3,
                          ease: "easeIn",
                        }}
                      />
                    ))}
                  </>
                )}

                {/* Agent Orb */}
                <motion.div
                  className={cn(
                    "w-14 h-14 rounded-full flex items-center justify-center text-2xl relative",
                    agent.color,
                    isActive && agent.glowColor,
                    hasCompleted && "opacity-60"
                  )}
                  animate={isActive ? {
                    scale: [1, 1.15, 1],
                  } : {}}
                  transition={{ duration: 0.8, repeat: isActive ? Infinity : 0 }}
                >
                  {hasCompleted && !isActive ? (
                    <span className="text-xl">✓</span>
                  ) : (
                    agent.icon
                  )}

                  {/* Pulse ring for active agent */}
                  {isActive && (
                    <motion.div
                      className="absolute inset-0 rounded-full border-2"
                      style={{ borderColor: agent.gradientFrom }}
                      initial={{ scale: 1, opacity: 0.8 }}
                      animate={{ scale: 1.5, opacity: 0 }}
                      transition={{ duration: 1, repeat: Infinity }}
                    />
                  )}
                </motion.div>
              </motion.div>
            );
          })}

          {/* Connection lines between agents during synthesis */}
          {phase === 'synthesis' && (
            <svg className="absolute inset-0 pointer-events-none" viewBox="-144 -144 288 288">
              {[0, 1, 2].map((i) => {
                const nextI = (i + 1) % 3;
                const angle1 = (i * 120 - 90) * (Math.PI / 180);
                const angle2 = (nextI * 120 - 90) * (Math.PI / 180);
                const r = 100;

                return (
                  <motion.line
                    key={i}
                    x1={Math.cos(angle1) * r}
                    y1={Math.sin(angle1) * r}
                    x2={Math.cos(angle2) * r}
                    y2={Math.sin(angle2) * r}
                    stroke="rgba(139, 92, 246, 0.3)"
                    strokeWidth="1"
                    strokeDasharray="4 4"
                    initial={{ opacity: 0 }}
                    animate={{
                      opacity: [0.2, 0.5, 0.2],
                      strokeDashoffset: [0, 8],
                    }}
                    transition={{
                      opacity: { duration: 1, repeat: Infinity },
                      strokeDashoffset: { duration: 1, repeat: Infinity, ease: "linear" },
                    }}
                  />
                );
              })}
            </svg>
          )}
        </div>
      </div>

      {/* Status Text */}
      <motion.div
        key={message.main}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-center mb-6"
      >
        <h3 className="text-xl font-semibold mb-1">{message.main}</h3>
        <p className="text-muted-foreground text-sm">{message.sub}</p>
      </motion.div>

      {/* Enhanced Progress Bar */}
      <div className="w-80 mb-6">
        {/* Phase indicators */}
        <div className="flex justify-between text-[10px] text-muted-foreground mb-2">
          <span className={cn(phase !== 'agents' && 'text-success')}>
            {phase !== 'agents' ? '✓' : '⚡'} Agents
          </span>
          <span className={cn(
            phase === 'receiving' && 'text-primary',
            phase === 'synthesis' || phase === 'complete' ? 'text-success' : ''
          )}>
            {phase === 'synthesis' || phase === 'complete' ? '✓' : phase === 'receiving' ? '⚡' : '○'} Receiving
          </span>
          <span className={cn(
            phase === 'synthesis' && 'text-primary',
            phase === 'complete' && 'text-success'
          )}>
            {phase === 'complete' ? '✓' : phase === 'synthesis' ? '⚡' : '○'} Synthesis
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-secondary rounded-full overflow-hidden relative">
          <motion.div
            className="h-full rounded-full absolute inset-0"
            style={{
              background: phase === 'synthesis' || phase === 'complete'
                ? 'linear-gradient(90deg, #3b82f6, #8b5cf6, #a855f7)'
                : 'linear-gradient(90deg, #3b82f6, #6366f1)',
            }}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />

          {/* Shimmer effect */}
          <motion.div
            className="absolute inset-0 opacity-30"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)',
            }}
            animate={{ x: ['-100%', '100%'] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>

        {/* Percentage */}
        <div className="text-right mt-1">
          <span className="text-xs font-mono text-muted-foreground">{Math.round(progress)}%</span>
        </div>
      </div>

      {/* Timeline */}
      <div className="flex items-center gap-2">
        {agents.map((agent, index) => (
          <div key={agent.name} className="flex items-center">
            <motion.div
              className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center text-sm transition-all duration-300",
                index < currentAgent || progress >= 75 ? agent.color :
                  index === currentAgent && progress < 75 ? `${agent.color} animate-pulse` :
                    'bg-secondary'
              )}
            >
              {index < currentAgent || progress >= 75 ? '✓' : agent.icon}
            </motion.div>
            {index < agents.length - 1 && (
              <motion.div
                className={cn(
                  "w-8 h-0.5 mx-1 transition-colors duration-300",
                  index < currentAgent || progress >= 75 ? 'bg-success' : 'bg-secondary'
                )}
              />
            )}
          </div>
        ))}
        <div className="flex items-center">
          <motion.div className="w-8 h-0.5 mx-1 bg-secondary" />
          <motion.div
            className={cn(
              "w-10 h-10 rounded-xl flex items-center justify-center text-lg transition-all duration-300",
              progress >= 75
                ? 'bg-gradient-to-br from-primary to-agent-trajectory shadow-lg shadow-primary/30'
                : 'bg-secondary'
            )}
            animate={progress >= 75 ? {
              scale: [1, 1.1, 1],
            } : {}}
            transition={{ duration: 1, repeat: progress >= 75 && progress < 100 ? Infinity : 0 }}
          >
            {progress >= 100 ? '✓' : '🧠'}
          </motion.div>
        </div>
      </div>
    </div>
  );
};
