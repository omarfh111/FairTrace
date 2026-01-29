
import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface StarFieldProps {
    count?: number;
    depth?: number;
}

export function StarField({ count = 5000, depth = 50 }: StarFieldProps) {
    const mesh = useRef<THREE.InstancedMesh>(null);

    // Generate random star positions and attributes
    const { positions, scales, colors, speeds } = useMemo(() => {
        const positions = new Float32Array(count * 3);
        const scales = new Float32Array(count);
        const colors = new Float32Array(count * 3);
        const speeds = new Float32Array(count);

        const colorChoices = [
            new THREE.Color('#ffffff'), // White
            new THREE.Color('#a5b4fc'), // Blue-ish
            new THREE.Color('#fcd34d'), // Yellow-ish
            new THREE.Color('#f472b6'), // Pink-ish
        ];

        for (let i = 0; i < count; i++) {
            // Random position in a sphere
            const r = depth + Math.random() * depth;
            const theta = 2 * Math.PI * Math.random();
            const phi = Math.acos(2 * Math.random() - 1);

            positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);

            // Random scale
            scales[i] = Math.random() * 0.5 + 0.1;

            // Random color
            const color = colorChoices[Math.floor(Math.random() * colorChoices.length)];
            colors[i * 3] = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;

            // Twinkle speed
            speeds[i] = Math.random() * 2 + 0.5;
        }

        return { positions, scales, colors, speeds };
    }, [count, depth]);

    const dummy = useMemo(() => new THREE.Object3D(), []);

    useFrame((state) => {
        if (!mesh.current) return;

        const time = state.clock.elapsedTime;

        for (let i = 0; i < count; i++) {
            // Twinkle effect using scale
            const s = scales[i] * (0.8 + 0.4 * Math.sin(time * speeds[i] + i));

            dummy.position.set(
                positions[i * 3],
                positions[i * 3 + 1],
                positions[i * 3 + 2]
            );
            dummy.scale.set(s, s, s);
            dummy.updateMatrix();

            mesh.current.setMatrixAt(i, dummy.matrix);
        }
        mesh.current.instanceMatrix.needsUpdate = true;

        // Slow rotation of the entire field
        mesh.current.rotation.y = time * 0.02;
        mesh.current.rotation.x = time * 0.005;
    });

    return (
        <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
            <sphereGeometry args={[0.05, 8, 8]} />
            <meshBasicMaterial vertexColors toneMapped={false} />
        </instancedMesh>
    );
}
