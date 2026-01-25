import { useRef, useMemo } from 'react';
import { useFrame, extend } from '@react-three/fiber';
import { Line } from '@react-three/drei';
import * as THREE from 'three';

interface CentralNexusProps {
  progress: number;
  orbPositions: THREE.Vector3[];
}

export const CentralNexus = ({ progress, orbPositions }: CentralNexusProps) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const innerMeshRef = useRef<THREE.Mesh>(null);
  const wireframeRef = useRef<THREE.Group>(null);

  const wireframeMaterial = useMemo(() => {
    return new THREE.MeshBasicMaterial({
      color: new THREE.Color('#8b5cf6'),
      wireframe: true,
      transparent: true,
      opacity: 0.6,
    });
  }, []);

  const innerMaterial = useMemo(() => {
    return new THREE.MeshStandardMaterial({
      color: new THREE.Color('#6366f1'),
      emissive: new THREE.Color('#8b5cf6'),
      emissiveIntensity: 0.5,
      transparent: true,
      opacity: 0.3,
      side: THREE.DoubleSide,
    });
  }, []);

  // Calculate proximity to orbs for pulsing
  const proximityPulse = useMemo(() => {
    if (orbPositions.length === 0) return 0;
    const avgDistance = orbPositions.reduce((sum, pos) => sum + pos.length(), 0) / orbPositions.length;
    return Math.max(0, 1 - avgDistance / 3);
  }, [orbPositions]);

  useFrame((state) => {
    if (!meshRef.current) return;

    const time = state.clock.elapsedTime;

    // Rotate the nexus with Y-axis rotation
    meshRef.current.rotation.x = time * 0.2;
    meshRef.current.rotation.y = time * 0.3;

    if (innerMeshRef.current) {
      innerMeshRef.current.rotation.x = -time * 0.15;
      innerMeshRef.current.rotation.y = -time * 0.25;
    }

    // Pulse based on progress and proximity to orbs
    const basePulse = Math.sin(time * 2) * 0.1 + 1;
    const proximityBoost = proximityPulse * 0.3;
    const progressScale = 0.5 + (progress / 100) * 0.5;
    meshRef.current.scale.setScalar((basePulse + proximityBoost) * progressScale);

    // Update emissive intensity based on progress and proximity
    if (innerMaterial) {
      innerMaterial.emissiveIntensity = 0.3 + (progress / 100) * 1.5 + proximityBoost * 2;
    }

    // Animate wireframe edges with energy flow
    if (wireframeRef.current) {
      wireframeRef.current.children.forEach((child, i) => {
        if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshBasicMaterial) {
          const energyFlow = Math.sin(time * 3 + i * 0.5) * 0.5 + 0.5;
          child.material.opacity = 0.3 + energyFlow * 0.5 * (progress / 100);
        }
      });
    }
  });

  // Create progress ring points
  const progressRingPoints = useMemo((): [number, number, number][] => {
    const segments = 64;
    const radius = 0.8;
    const progressAngle = (progress / 100) * Math.PI * 2;
    
    const points: [number, number, number][] = [];
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * progressAngle - Math.PI / 2;
      points.push([
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
        0
      ] as [number, number, number]);
    }
    
    return points.length >= 2 ? points : [[0, 0, 0], [0, 0, 0]];
  }, [progress]);

  // Progress ring color based on progress
  const progressColor = useMemo(() => {
    if (progress < 33) return '#8b5cf6'; // Purple
    if (progress < 66) return '#3b82f6'; // Blue
    return '#10b981'; // Green
  }, [progress]);

  // Create wireframe edges for energy flow
  const wireframeEdges = useMemo(() => {
    const edges: JSX.Element[] = [];
    const geometry = new THREE.IcosahedronGeometry(0.5, 1);
    const edgeGeometry = new THREE.EdgesGeometry(geometry);
    const positions = edgeGeometry.attributes.position.array;
    
    for (let i = 0; i < positions.length; i += 6) {
      const x1 = positions[i];
      const y1 = positions[i + 1];
      const z1 = positions[i + 2];
      const x2 = positions[i + 3];
      const y2 = positions[i + 4];
      const z2 = positions[i + 5];
      
      edges.push(
        <mesh key={i} position={[(x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2]}>
          <boxGeometry args={[0.02, 0.02, Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)]} />
          <meshBasicMaterial color="#8b5cf6" transparent opacity={0.6} />
        </mesh>
      );
    }
    
    return edges;
  }, []);

  return (
    <group>
      {/* Main wireframe icosahedron */}
      <mesh ref={meshRef} material={wireframeMaterial}>
        <icosahedronGeometry args={[0.5, 1]} />
      </mesh>

      {/* Energy flow wireframe edges */}
      <group ref={wireframeRef}>
        {wireframeEdges}
      </group>

      {/* Inner glowing core */}
      <mesh ref={innerMeshRef} material={innerMaterial} scale={0.35}>
        <dodecahedronGeometry args={[1, 0]} />
      </mesh>

      {/* Center point light */}
      <pointLight
        color="#8b5cf6"
        intensity={1 + (progress / 100) * 3}
        distance={5}
        decay={2}
      />

      {/* Progress ring */}
      {progressRingPoints.length >= 2 && (
        <Line
          points={progressRingPoints}
          color={progressColor}
          lineWidth={2}
          transparent
          opacity={0.8}
        />
      )}

      {/* Connection lines to orbs with color tint */}
      {orbPositions.map((pos, i) => {
        const distance = pos.length();
        const opacity = Math.max(0, 1 - distance / 3) * (progress / 100);
        
        if (opacity < 0.1) return null;
        
        const colors = ['#ef4444', '#10b981', '#3b82f6'];
        
        return (
          <Line
            key={i}
            points={[[0, 0, 0], [pos.x, pos.y, pos.z]]}
            color={colors[i]}
            lineWidth={1.5}
            transparent
            opacity={opacity}
          />
        );
      })}
    </group>
  );
};
