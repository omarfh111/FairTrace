
import { motion, AnimatePresence } from 'framer-motion';

interface HolographicUIProps {
    progress: number;
    message: string;
}

export function HolographicUI({ progress, message }: HolographicUIProps) {
    return (
        <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-between py-12 z-10 selection:bg-none">

            {/* Top Header */}
            <motion.div
                className="text-center space-y-2"
                initial={{ opacity: 0, y: -50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1 }}
            >
                <div className="flex items-center gap-3 justify-center mb-2">
                    <div className="h-[1px] w-12 bg-gradient-to-r from-transparent to-cyan-500/50" />
                    <h1 className="text-3xl md:text-5xl font-bold tracking-[0.2em] font-orbitron text-transparent bg-clip-text bg-gradient-to-b from-cyan-100 to-cyan-500 drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
                        FAIRTRACE
                    </h1>
                    <div className="h-[1px] w-12 bg-gradient-to-l from-transparent to-cyan-500/50" />
                </div>
                <p className="text-cyan-400/60 text-xs md:text-sm tracking-[0.4em] uppercase">
                    Orbital Intelligence System
                </p>
            </motion.div>

            {/* Center - Percentage & Status */}
            <div className="flex flex-col items-center justify-center gap-6 w-full max-w-md">

                {/* Holographic Containment Ring */}
                <div className="relative flex items-center justify-center w-64 h-64 md:w-80 md:h-80">
                    {/* Spinning Rings (CSS animation could be added here or via Framer Motion) */}
                    <motion.div
                        className="absolute inset-0 border border-cyan-500/20 rounded-full"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                    />
                    <motion.div
                        className="absolute inset-4 border border-dashed border-cyan-400/30 rounded-full"
                        animate={{ rotate: -360 }}
                        transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                    />

                    {/* Percentage Number */}
                    <div className="relative z-10 flex flex-col items-center">
                        <motion.span
                            className="text-6xl md:text-8xl font-mono font-bold text-white tabular-nums drop-shadow-[0_0_15px_rgba(255,255,255,0.8)]"
                            key={Math.floor(progress)}
                        >
                            {Math.floor(progress)}<span className="text-3xl md:text-4xl text-cyan-400/80 align-top">%</span>
                        </motion.span>
                    </div>
                </div>

                {/* Loading Bar */}
                <div className="w-full h-1 bg-cyan-900/30 rounded-full overflow-hidden backdrop-blur-sm border border-cyan-500/10 relative">
                    <motion.div
                        className="h-full bg-gradient-to-r from-cyan-600 via-blue-500 to-purple-500 shadow-[0_0_15px_rgba(56,189,248,0.6)]"
                        style={{ width: `${progress}%` }}
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                    />
                    {/* Moving Scanner Effect */}
                    <motion.div
                        className="absolute top-0 bottom-0 w-20 bg-gradient-to-r from-transparent via-white/40 to-transparent"
                        animate={{ x: [-100, 500] }}
                        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    />
                </div>

                {/* Status Message */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={message}
                        initial={{ opacity: 0, y: 10, filter: 'blur(5px)' }}
                        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                        exit={{ opacity: 0, y: -10, filter: 'blur(5px)' }}
                        className="bg-black/40 backdrop-blur-md border border-cyan-500/20 px-6 py-2 rounded-full"
                    >
                        <p className="text-cyan-300 font-mono text-sm tracking-widest uppercase">
                            <span className="animate-pulse mr-2">▶</span>
                            {message}
                        </p>
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* Footer System Info */}
            <div className="flex justify-between w-full max-w-4xl px-8 text-[10px] text-cyan-500/40 font-mono uppercase tracking-wider">
                <div>Sys.Ver: 2.4.9b</div>
                <div>Sector: 7G-Alpha</div>
                <div>Mem: Optimized</div>
            </div>

        </div>
    );
}
