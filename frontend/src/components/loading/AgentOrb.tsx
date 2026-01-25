import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere, Trail } from '@react-three/drei';
import * as THREE from 'three';

interface AgentOrbProps {
  color: string;
  secondaryColor: string;
  orbitRadius: number;
  orbitSpeed: number;
  orbitOffset: number;
  orbitTilt: number;
  pulseSpeed: number;
  pulseIntensity: number;
  visible: boolean;
  progress: number;
  isErratic?: boolean;
  isParabolic?: boolean;
}

export const AgentOrb = ({
  color,
  secondaryColor,
  orbitRadius,
  orbitSpeed,
  orbitOffset,
  orbitTilt,
  pulseSpeed,
  pulseIntensity,
  visible,
  progress,
  isErratic = false,
  isParabolic = false,
}: AgentOrbProps) => {
  const orbRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const groupRef = useRef<THREE.Group>(null);

  const orbMaterial = useMemo(() => {
    return new THREE.MeshStandardMaterial({
      color: new THREE.Color(color),
      emissive: new THREE.Color(color),
      emissiveIntensity: 2,
      toneMapped: false,
    });
  }, [color]);

  const glowMaterial = useMemo(() => {
    return new THREE.MeshBasicMaterial({
      color: new THREE.Color(color),
      transparent: true,
      opacity: 0.3,
    });
  }, [color]);

  // Trail configuration based on agent type
  const trailConfig = useMemo(() => {
    if (color === '#ef4444') {
      // Red embers for Risk
      return { width: 0.4, length: 8, decay: 0.95 };
    } else if (color === '#10b981') {
      // Smooth green for Fairness
      return { width: 0.25, length: 6, decay: 0.9 };
    } else {
      // Blue streaks for Trajectory
      return { width: 0.3, length: 7, decay: 0.92 };
    }
  }, [color]);

  useFrame((state) => {
    if (!orbRef.current || !groupRef.current || !visible) return;

    const time = state.clock.elapsedTime;
    const stabilization = Math.min(1, progress / 75);

    // Calculate orbital position
    let angle = time * orbitSpeed + orbitOffset;
    let x = Math.cos(angle) * orbitRadius;
    let z = Math.sin(angle) * orbitRadius;
    let y = 0;

    // Add orbit characteristics based on type
    if (isErratic && stabilization < 1) {
      const erraticAmount = (1 - stabilization) * 0.5;
      x += Math.sin(time * 3) * erraticAmount;
      y += Math.cos(time * 4) * erraticAmount;
      z += Math.sin(time * 2.5) * erraticAmount;
    }

    if (isParabolic) {
      y = Math.sin(angle * 2) * 0.5 * (1 - stabilization * 0.5);
    }

    // Apply tilt
    const tiltedY = y * Math.cos(orbitTilt) - z * Math.sin(orbitTilt);
    const tiltedZ = y * Math.sin(orbitTilt) + z * Math.cos(orbitTilt);

    groupRef.current.position.set(x, tiltedY, tiltedZ);

    // Pulse/breathe effect (scale 0.95 → 1.05)
    const breathe = Math.sin(time * pulseSpeed) * 0.05;
    const pulse = 1 + breathe;
    orbRef.current.scale.setScalar(0.15 * pulse);

    // Update emissive intensity
    if (orbMaterial) {
      orbMaterial.emissiveIntensity = 1.5 + breathe * 10;
    }

    // Glow scale with soft halo
    if (glowRef.current) {
      glowRef.current.scale.setScalar(0.5 * pulse);
      (glowRef.current.material as THREE.MeshBasicMaterial).opacity = 0.15 + breathe * 2;
    }
  });

  if (!visible) return null;

  return (
    <group ref={groupRef}>
      <Trail
        width={trailConfig.width}
        length={trailConfig.length}
        color={new THREE.Color(color)}
        attenuation={(t) => Math.pow(t, trailConfig.decay)}
      >
        <mesh ref={orbRef} material={orbMaterial}>
          <sphereGeometry args={[0.15, 32, 32]} />
        </mesh>
      </Trail>
      
      {/* Outer glow halo */}
      <mesh ref={glowRef} material={glowMaterial}>
        <sphereGeometry args={[0.5, 16, 16]} />
      </mesh>
      
      {/* Inner bright core */}
      <mesh scale={0.06}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color="white" />
      </mesh>
    </group>
  );
};
