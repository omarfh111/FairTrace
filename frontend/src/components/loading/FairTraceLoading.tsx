
import { useState, useEffect, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { EffectComposer, Bloom, Vignette, Noise } from '@react-three/postprocessing';
import { motion, AnimatePresence } from 'framer-motion';
import { StarField } from './StarField';
import { OrbitalSystem } from './OrbitalSystem';
import { SpaceNebula } from './SpaceNebula';
import { MeteorSystem } from './MeteorSystem';
import { HolographicUI } from './HolographicUI';
import { PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';

interface FairTraceLoadingProps {
  onLoadingComplete: () => void;
  duration?: number;
}

const loadingMessages = [
  'Initializing Orbital Systems...',
  'Aligning Satellite Arrays...',
  'Calculating Trajectories...',
  'Establishing Secure Connection...',
  'Warp Drive Engaging...',
  'System Ready',
];

export const FairTraceLoading = ({ onLoadingComplete, duration = 8000 }: FairTraceLoadingProps) => {
  const [progress, setProgress] = useState(0);
  const [currentMessage, setCurrentMessage] = useState(0);
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const newProgress = Math.min(100, (elapsed / duration) * 100);
      setProgress(newProgress);

      // Update messages based on progress chunks
      const msgIndex = Math.min(
        Math.floor((newProgress / 100) * loadingMessages.length),
        loadingMessages.length - 1
      );
      setCurrentMessage(msgIndex);

      if (newProgress >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          setIsFadingOut(true);
          setTimeout(onLoadingComplete, 1200); // Wait for exit animation
        }, 500);
      }
    }, 16);

    return () => clearInterval(interval);
  }, [duration, onLoadingComplete]);

  return (
    <AnimatePresence>
      {!isFadingOut && (
        <motion.div
          className="fixed inset-0 z-50 bg-[#050508] overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{
            opacity: 0,
            scale: 1.5,
            filter: 'brightness(20)', // Flash effect on exit
            transition: { duration: 1.2, ease: "easeInOut" }
          }}
        >
          {/* 3D Scene */}
          <Canvas gl={{ antialias: false, toneMapping: THREE.ReinhardToneMapping }}>
            {/* Camera with subtle movement */}
            <PerspectiveCamera makeDefault position={[0, 2, 12]} fov={50} />

            {/* Scene Lighting */}
            <ambientLight intensity={0.1} />
            <pointLight position={[10, 10, 10]} intensity={1} color="#4c1d95" />
            <pointLight position={[-10, -5, -10]} intensity={0.5} color="#be185d" />

            <Suspense fallback={null}>
              <StarField count={6000} depth={60} />
              <SpaceNebula />
              <OrbitalSystem progress={progress} />
              <MeteorSystem count={25} />

              {/* Post Processing */}
              <EffectComposer>
                <Bloom
                  luminanceThreshold={0.2}
                  mipmapBlur
                  intensity={1.5}
                  radius={0.6}
                />
                <Noise opacity={0.05} />
                <Vignette eskil={false} offset={0.1} darkness={1.1} />
              </EffectComposer>
            </Suspense>
          </Canvas>

          {/* UI Overlay */}
          <HolographicUI progress={progress} message={loadingMessages[currentMessage]} />

        </motion.div>
      )}
    </AnimatePresence>
  );
};

