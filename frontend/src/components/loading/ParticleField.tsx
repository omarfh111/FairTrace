import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface ParticleFieldProps {
  count?: number;
  progress: number;
  phase?: number;
}

export const ParticleField = ({ count = 2000, progress, phase = 4 }: ParticleFieldProps) => {
  const pointsRef = useRef<THREE.Points>(null);

  const { positions, velocities, sizes, colors } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    const colors = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      // Spread particles in a sphere
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 3 + Math.random() * 7;

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      // Random velocities
      velocities[i * 3] = (Math.random() - 0.5) * 0.002;
      velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.002;
      velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.002;

      // Random sizes
      sizes[i] = Math.random() * 2 + 0.5;

      // Default white color
      colors[i * 3] = 1;
      colors[i * 3 + 1] = 1;
      colors[i * 3 + 2] = 1;
    }

    return { positions, velocities, sizes, colors };
  }, [count]);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    return geo;
  }, [positions, sizes, colors]);

  const material = useMemo(() => {
    return new THREE.PointsMaterial({
      size: 0.03,
      vertexColors: true,
      transparent: true,
      opacity: 0.4,
      sizeAttenuation: true,
      blending: THREE.AdditiveBlending,
    });
  }, []);

  useFrame(() => {
    if (!pointsRef.current) return;

    const positionArray = pointsRef.current.geometry.attributes.position.array as Float32Array;
    const colorArray = pointsRef.current.geometry.attributes.color.array as Float32Array;

    // Phase-based behavior
    const isMaterializing = phase === 1;
    const isChaotic = phase === 2;
    const isSynchronizing = phase === 3;
    const isStable = phase >= 4;

    for (let i = 0; i < count; i++) {
      // Chaotic phase - faster movement
      const speedMultiplier = isChaotic ? 3 : isSynchronizing ? 1.5 : 1;
      
      positionArray[i * 3] += velocities[i * 3] * speedMultiplier;
      positionArray[i * 3 + 1] += velocities[i * 3 + 1] * speedMultiplier;
      positionArray[i * 3 + 2] += velocities[i * 3 + 2] * speedMultiplier;

      // Wrap around if too far
      const distance = Math.sqrt(
        positionArray[i * 3] ** 2 +
        positionArray[i * 3 + 1] ** 2 +
        positionArray[i * 3 + 2] ** 2
      );

      if (distance > 12) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const radius = 3;

        positionArray[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
        positionArray[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
        positionArray[i * 3 + 2] = radius * Math.cos(phi);
      }

      // Color based on phase
      if (isChaotic) {
        // Red tint for chaotic phase
        colorArray[i * 3] = 1;
        colorArray[i * 3 + 1] = 0.5;
        colorArray[i * 3 + 2] = 0.5;
      } else if (isSynchronizing) {
        // Blue tint for synchronizing
        colorArray[i * 3] = 0.5;
        colorArray[i * 3 + 1] = 0.7;
        colorArray[i * 3 + 2] = 1;
      } else if (isStable) {
        // Green tint for stable
        colorArray[i * 3] = 0.5;
        colorArray[i * 3 + 1] = 1;
        colorArray[i * 3 + 2] = 0.7;
      } else {
        // White for materializing
        colorArray[i * 3] = 1;
        colorArray[i * 3 + 1] = 1;
        colorArray[i * 3 + 2] = 1;
      }
    }

    pointsRef.current.geometry.attributes.position.needsUpdate = true;
    pointsRef.current.geometry.attributes.color.needsUpdate = true;

    // Subtle rotation - faster in chaotic phase
    const rotationSpeed = isChaotic ? 0.001 : isSynchronizing ? 0.0005 : 0.0002;
    pointsRef.current.rotation.y += rotationSpeed;
  });

  return (
    <points ref={pointsRef} geometry={geometry} material={material} />
  );
};
