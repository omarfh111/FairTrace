
import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Cloud } from '@react-three/drei';
import * as THREE from 'three';

export function SpaceNebula() {
    const group = useRef<THREE.Group>(null);

    useFrame((state) => {
        if (group.current) {
            group.current.rotation.y = state.clock.elapsedTime * 0.01;
        }
    });

    return (
        <group ref={group}>
            {/* Deep Purple/Blue Nebula Background */}
            <Cloud
                opacity={0.3}
                speed={0.1}
                bounds={[30, 5, 30]}
                segments={20}
                color="#4c1d95" // Deep Purple
                position={[-10, 0, -20]}
            />
            <Cloud
                opacity={0.2}
                speed={0.1}
                bounds={[30, 5, 30]}
                segments={20}
                color="#1e40af" // Blue
                position={[10, 5, -25]}
            />
            <Cloud
                opacity={0.1}
                speed={0.05}
                bounds={[40, 10, 40]}
                segments={30}
                color="#be185d" // Pinkish hue
                position={[0, -10, -30]}
            />
        </group>
    );
}
