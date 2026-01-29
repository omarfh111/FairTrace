
import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Line, Ring } from '@react-three/drei';
import * as THREE from 'three';

interface OrbitalSystemProps {
    progress: number;
}

export function OrbitalSystem({ progress }: OrbitalSystemProps) {
    const planetGroup = useRef<THREE.Group>(null);

    // Orbit paths data
    const orbits = useMemo(() => [
        { radius: 3, speed: 0.4, tilt: 0.2, color: '#3b82f6', size: 0.3 }, // Inner Blue
        { radius: 5, speed: 0.2, tilt: -0.1, color: '#10b981', size: 0.4 }, // Mid Green
        { radius: 8, speed: 0.1, tilt: 0.4, color: '#f43f5e', size: 0.6 }, // Outer Red
    ], []);

    useFrame((state) => {
        const time = state.clock.elapsedTime;

        if (planetGroup.current) {
            // Animate planets along orbits
            planetGroup.current.children.forEach((child, i) => {
                const orbit = orbits[i];
                if (!orbit) return;

                const angle = time * orbit.speed + (i * Math.PI * 2) / 3;
                child.position.x = Math.cos(angle) * orbit.radius;
                child.position.z = Math.sin(angle) * orbit.radius;

                // Add some bobbing
                child.position.y = Math.sin(time + i) * 0.2;

                child.rotation.y += 0.01;
            });
        }
    });

    return (
        <group rotation={[0.2, 0, 0]}>
            {/* Draw Orbit Lines */}
            {orbits.map((orbit, i) => (
                <group key={`orbit-${i}`} rotation={[orbit.tilt, 0, 0]}>
                    <Ring
                        args={[orbit.radius, orbit.radius + 0.02, 128]}
                        rotation={[-Math.PI / 2, 0, 0]}
                    >
                        <meshBasicMaterial
                            color={orbit.color}
                            transparent
                            opacity={0.15}
                            side={THREE.DoubleSide}
                            blending={THREE.AdditiveBlending}
                        />
                    </Ring>

                    {/* Secondary thin line for detail */}
                    <Line
                        points={new THREE.EllipseCurve(0, 0, orbit.radius, orbit.radius, 0, 2 * Math.PI, false, 0).getPoints(100)}
                        color={orbit.color}
                        lineWidth={1}
                        transparent
                        opacity={0.1}
                        rotation={[-Math.PI / 2, 0, 0]}
                    />
                </group>
            ))}

            {/* Planets */}
            <group ref={planetGroup}>
                {orbits.map((orbit, i) => (
                    <group key={`planet-${i}`} rotation={[orbit.tilt, 0, 0]}>
                        <mesh>
                            <sphereGeometry args={[orbit.size, 32, 32]} />
                            <meshStandardMaterial
                                color={orbit.color}
                                emissive={orbit.color}
                                emissiveIntensity={0.5}
                                roughness={0.7}
                                metalness={0.2}
                            />
                            <pointLight color={orbit.color} intensity={1} distance={3} />
                        </mesh>
                    </group>
                ))}
            </group>

            {/* Central Sun/Core */}
            <mesh>
                <sphereGeometry args={[1, 64, 64]} />
                <meshStandardMaterial
                    color="#f59e0b"
                    emissive="#f59e0b"
                    emissiveIntensity={2}
                    toneMapped={false}
                />
                <pointLight color="#f59e0b" intensity={2} distance={10} />
            </mesh>
        </group>
    );
}
