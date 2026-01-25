import { useRef, useState, useEffect, useMemo, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Stars, Trail } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';
import { motion, AnimatePresence } from 'framer-motion';
import { AgentOrb } from './AgentOrb';
import { CentralNexus } from './CentralNexus';
import { ParticleField } from './ParticleField';

// Completion burst effect component
const CompletionBurst = () => {
  const particlesRef = useRef<THREE.Points>(null);
  const [particles] = useState(() => {
    const count = 500;
    const positions = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);
    
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const speed = 0.1 + Math.random() * 0.2;
      
      positions[i * 3] = 0;
      positions[i * 3 + 1] = 0;
      positions[i * 3 + 2] = 0;
      
      velocities[i * 3] = Math.sin(phi) * Math.cos(theta) * speed;
      velocities[i * 3 + 1] = Math.sin(phi) * Math.sin(theta) * speed;
      velocities[i * 3 + 2] = Math.cos(phi) * speed;
    }
    
    return { positions, velocities, count };
  });

  useFrame(() => {
    if (!particlesRef.current) return;
    
    const positions = particlesRef.current.geometry.attributes.position.array as Float32Array;
    
    for (let i = 0; i < particles.count; i++) {
      positions[i * 3] += particles.velocities[i * 3];
      positions[i * 3 + 1] += particles.velocities[i * 3 + 1];
      positions[i * 3 + 2] += particles.velocities[i * 3 + 2];
      
      // Slow down
      particles.velocities[i * 3] *= 0.98;
      particles.velocities[i * 3 + 1] *= 0.98;
      particles.velocities[i * 3 + 2] *= 0.98;
    }
    
    particlesRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={particlesRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={particles.count}
          array={particles.positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.08}
        color="#ffffff"
        transparent
        opacity={1}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
};

interface LoadingSceneProps {
  progress: number;
  phase: number;
  mousePosition: THREE.Vector2;
}

const LoadingScene = ({ progress, phase, mousePosition }: LoadingSceneProps) => {
  const { camera } = useThree();
  const cameraGroupRef = useRef<THREE.Group>(null);
  const [orbPositions, setOrbPositions] = useState<THREE.Vector3[]>([
    new THREE.Vector3(),
    new THREE.Vector3(),
    new THREE.Vector3(),
  ]);

  // Animate camera with mouse parallax
  useFrame((state) => {
    const time = state.clock.elapsedTime;
    
    // Slow cinematic rotation (20-second loop)
    const cameraAngle = time * 0.05; // ~20 seconds for full rotation
    camera.position.x = Math.sin(cameraAngle) * 5;
    camera.position.z = Math.cos(cameraAngle) * 5;
    camera.position.y = 1.5 + Math.sin(time * 0.15) * 0.5;
    
    // Mouse parallax effect
    camera.position.x += mousePosition.x * 0.5;
    camera.position.y += mousePosition.y * 0.3;
    
    camera.lookAt(0, 0, 0);

    // Zoom based on progress
    const targetDistance = 5 - (progress / 100) * 1;
    const currentDistance = camera.position.length();
    const newDistance = THREE.MathUtils.lerp(currentDistance, targetDistance, 0.01);
    camera.position.normalize().multiplyScalar(newDistance);
  });

  // Update orb positions for connection lines with mouse attraction
  useFrame((state) => {
    const time = state.clock.elapsedTime;
    const stabilization = Math.min(1, progress / 75);
    
    // Phase-based behavior
    const isMaterializing = phase === 1;
    const isChaotic = phase === 2;
    const isSynchronizing = phase === 3;
    const isStable = phase >= 4;

    // Mouse attraction strength based on phase
    const attractionStrength = isStable ? 0 : 0.3 * (1 - stabilization);
    const mouseX = mousePosition.x * attractionStrength;
    const mouseY = mousePosition.y * attractionStrength;

    // Risk orb position
    let riskAngle = time * 0.5 + 0;
    let riskX = Math.cos(riskAngle) * 1.5;
    let riskZ = Math.sin(riskAngle) * 1.2;
    let riskY = Math.sin(time * 2.5) * 0.3 * (1 - stabilization);

    // Erratic behavior for Risk in chaotic phase
    if (isChaotic) {
      riskX += Math.sin(time * 3) * 0.3;
      riskY += Math.cos(time * 4) * 0.3;
      riskZ += Math.sin(time * 2.5) * 0.3;
    }

    // Mouse attraction
    riskX += mouseX;
    riskY += mouseY;

    // Fairness orb position
    const fairnessAngle = time * 0.5 + (Math.PI * 2) / 3;
    let fairnessX = Math.cos(fairnessAngle) * 1.5;
    let fairnessZ = Math.sin(fairnessAngle) * 1.5;
    let fairnessY = 0;

    // Smooth green for Fairness - slight attraction
    fairnessX += mouseX * 0.5;
    fairnessY += mouseY * 0.5;

    // Trajectory orb position
    const trajectoryAngle = time * 0.5 + (Math.PI * 4) / 3;
    let trajectoryX = Math.cos(trajectoryAngle) * 1.5;
    let trajectoryZ = Math.sin(trajectoryAngle) * 1.5;
    let trajectoryY = Math.sin(trajectoryAngle * 2) * 0.5 * (1 - stabilization * 0.5);

    // Forward-moving parabolic trajectory
    trajectoryX += mouseX * 0.3;
    trajectoryY += mouseY * 0.3;

    // Materializing effect - scale from zero
    const scale = isMaterializing ? Math.min(1, progress / 25) : 1;

    setOrbPositions([
      new THREE.Vector3(riskX * scale, riskY * scale, riskZ * scale),
      new THREE.Vector3(fairnessX * scale, fairnessY * scale, fairnessZ * scale),
      new THREE.Vector3(trajectoryX * scale, trajectoryY * scale, trajectoryZ * scale),
    ]);
  });

  return (
    <>
      {/* Environment */}
      <color attach="background" args={['#050508']} />
      <fog attach="fog" args={['#050508', 5, 20]} />
      <ambientLight intensity={0.2} />
      
      {/* Star field */}
      <Stars
        radius={50}
        depth={50}
        count={3000}
        factor={3}
        saturation={0.5}
        fade
        speed={0.5}
      />

      {/* Central Nexus */}
      <CentralNexus progress={progress} orbPositions={orbPositions} />

      {/* Agent Orbs */}
      <AgentOrb
        color="#ef4444"
        secondaryColor="#dc2626"
        orbitRadius={1.5}
        orbitSpeed={0.5}
        orbitOffset={0}
        orbitTilt={0.2}
        pulseSpeed={3}
        pulseIntensity={0.15}
        visible={phase >= 1}
        progress={progress}
        isErratic={true}
      />
      
      <AgentOrb
        color="#10b981"
        secondaryColor="#059669"
        orbitRadius={1.5}
        orbitSpeed={0.5}
        orbitOffset={(Math.PI * 2) / 3}
        orbitTilt={0}
        pulseSpeed={2}
        pulseIntensity={0.05}
        visible={phase >= 1}
        progress={progress}
      />
      
      <AgentOrb
        color="#3b82f6"
        secondaryColor="#2563eb"
        orbitRadius={1.5}
        orbitSpeed={0.5}
        orbitOffset={(Math.PI * 4) / 3}
        orbitTilt={-0.15}
        pulseSpeed={2.5}
        pulseIntensity={0.1}
        visible={phase >= 1}
        progress={progress}
        isParabolic={true}
      />

      {/* Particle Field */}
      <ParticleField count={1500} progress={progress} phase={phase} />

      {/* Post-processing */}
      <EffectComposer>
        <Bloom
          intensity={1.5}
          luminanceThreshold={0.2}
          luminanceSmoothing={0.9}
          mipmapBlur
        />
      </EffectComposer>
    </>
  );
};

interface FairTraceLoadingProps {
  onLoadingComplete: () => void;
  duration?: number;
}

const loadingMessages = [
  'Initializing Multi-Agent System...',
  'Calibrating Risk Models...',
  'Loading Historical Data...',
  'Establishing Secure Connection...',
  'System Ready',
];

export const FairTraceLoading = ({ onLoadingComplete, duration = 8000 }: FairTraceLoadingProps) => {
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState(0);
  const [currentMessage, setCurrentMessage] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [mousePosition, setMousePosition] = useState(new THREE.Vector2(0, 0));
  const [showBurst, setShowBurst] = useState(false);

  // Track mouse position
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = -(e.clientY / window.innerHeight) * 2 + 1;
      setMousePosition(new THREE.Vector2(x, y));
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    const startTime = Date.now();
    
    const progressInterval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const newProgress = Math.min(100, (elapsed / duration) * 100);
      setProgress(newProgress);

      // Update phase
      if (newProgress < 25) setPhase(1);
      else if (newProgress < 50) setPhase(2);
      else if (newProgress < 75) setPhase(3);
      else if (newProgress < 100) setPhase(4);
      else setPhase(5);

      // Update message
      const messageIndex = Math.min(
        Math.floor((newProgress / 100) * loadingMessages.length),
        loadingMessages.length - 1
      );
      setCurrentMessage(messageIndex);

      if (newProgress >= 100) {
        clearInterval(progressInterval);
        setIsComplete(true);
        setShowBurst(true);
        
        // Start fade out after brief pause
        setTimeout(() => {
          setIsFadingOut(true);
          setTimeout(onLoadingComplete, 800);
        }, 1000);
      }
    }, 16);

    return () => clearInterval(progressInterval);
  }, [duration, onLoadingComplete]);

  return (
    <AnimatePresence>
      {!isFadingOut && (
        <motion.div
          className="fixed inset-0 z-50 bg-[#050508]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8 }}
        >
          {/* 3D Canvas */}
          <Canvas
            camera={{ position: [0, 2, 5], fov: 50 }}
            gl={{ antialias: true, alpha: false }}
            dpr={[1, 2]}
          >
            <Suspense fallback={null}>
              <LoadingScene progress={progress} phase={phase} mousePosition={mousePosition} />
              {showBurst && <CompletionBurst />}
            </Suspense>
          </Canvas>

          {/* UI Overlay */}
          <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-between py-16">
            {/* Logo */}
            <motion.div
              className="text-center"
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.8 }}
            >
              <h1 className="text-5xl font-bold tracking-tight">
                <span className="bg-gradient-to-r from-violet-400 via-blue-400 to-emerald-400 bg-clip-text text-transparent">
                  FairTrace
                </span>
              </h1>
              <p className="text-sm text-white/40 mt-2 tracking-widest uppercase">
                Multi-Agent Credit Intelligence
              </p>
            </motion.div>

            {/* Progress Section */}
            <div className="flex flex-col items-center gap-8">
              {/* Percentage */}
              <motion.div
                className="relative"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.8, duration: 0.5 }}
              >
                <span className="text-8xl font-mono font-bold text-white tabular-nums tracking-tight">
                  {Math.floor(progress)}
                </span>
                <span className="text-4xl font-mono text-white/50 ml-2">%</span>
              </motion.div>

              {/* Progress Bar */}
              <div className="w-80 h-1 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{
                    background: progress < 33 
                      ? 'linear-gradient(90deg, #8b5cf6, #a78bfa)'
                      : progress < 66 
                        ? 'linear-gradient(90deg, #8b5cf6, #3b82f6)'
                        : 'linear-gradient(90deg, #3b82f6, #10b981)',
                    width: `${progress}%`,
                    boxShadow: '0 0 20px currentColor',
                  }}
                  transition={{ duration: 0.1 }}
                />
              </div>

              {/* Status Message */}
              <AnimatePresence mode="wait">
                <motion.p
                  key={currentMessage}
                  className="text-base text-white/70 font-medium tracking-wide"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.3 }}
                >
                  {loadingMessages[currentMessage]}
                </motion.p>
              </AnimatePresence>

              {/* Agent Status Indicators */}
              <div className="flex gap-6 mt-4">
                {[
                  { name: 'Risk Agent', color: '#ef4444', delay: 0 },
                  { name: 'Fairness Agent', color: '#10b981', delay: 0.2 },
                  { name: 'Trajectory Agent', color: '#3b82f6', delay: 0.4 },
                ].map((agent, i) => (
                  <motion.div
                    key={agent.name}
                    className="flex items-center gap-2"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: phase >= 1 ? 1 : 0.3, x: 0 }}
                    transition={{ delay: 1 + agent.delay, duration: 0.5 }}
                  >
                    <motion.div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: agent.color }}
                      animate={{
                        scale: phase >= 2 ? [1, 1.3, 1] : 1,
                        opacity: phase >= 2 ? 1 : 0.5,
                      }}
                      transition={{
                        scale: { repeat: Infinity, duration: 1.5, delay: i * 0.3 },
                      }}
                    />
                    <span className="text-xs text-white/40">{agent.name}</span>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Bottom Text */}
            <motion.p
              className="text-xs text-white/20"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 2 }}
            >
              Powered by Multi-Agent AI Architecture
            </motion.p>
          </div>

          {/* Completion Flash */}
          <AnimatePresence>
            {isComplete && (
              <motion.div
                className="absolute inset-0 bg-white pointer-events-none"
                initial={{ opacity: 0 }}
                animate={{ opacity: [0, 0.3, 0] }}
                transition={{ duration: 0.5 }}
              />
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
