
import { useRef, useMemo, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface MeteorProps {
    count?: number;
}

export function MeteorSystem({ count = 20 }: MeteorProps) {
    const lineRef = useRef<THREE.LineSegments>(null);

    // Pre-calculate random properties for meteors
    const meteors = useMemo(() => {
        return new Array(count).fill(0).map(() => ({
            position: new THREE.Vector3(
                (Math.random() - 0.5) * 100,
                (Math.random() - 0.5) * 60,
                (Math.random() - 0.5) * 40 - 20 // Mostly in background
            ),
            velocity: new THREE.Vector3(
                -1 - Math.random() * 2, // Move left
                -0.5 + Math.random(),   // Slight random Y
                0
            ),
            speed: 1 + Math.random() * 2,
            length: 2 + Math.random() * 5,
            active: Math.random() > 0.8, // Start some as active
            resetTimer: Math.random() * 100
        }));
    }, [count]);

    const geometry = useMemo(() => new THREE.BufferGeometry(), []);

    useFrame(() => {
        if (!lineRef.current) return;

        const positions: number[] = [];
        const colors: number[] = [];

        meteors.forEach(meteor => {
            if (meteor.active) {
                // Move meteor
                meteor.position.addScaledVector(meteor.velocity, meteor.speed * 0.2);

                // Calculate tail end position (behind current pos)
                const tailPos = meteor.position.clone().sub(
                    meteor.velocity.clone().normalize().multiplyScalar(meteor.length)
                );

                positions.push(
                    meteor.position.x, meteor.position.y, meteor.position.z,
                    tailPos.x, tailPos.y, tailPos.z
                );

                // Gradient color: Head white, tail transparent
                colors.push(
                    1, 1, 1, // Head
                    1, 1, 1  // Tail color (alpha handled by material)
                );

                // Reset if out of bounds
                if (meteor.position.x < -60 || meteor.position.y < -40 || meteor.position.y > 40) {
                    meteor.active = false;
                    meteor.resetTimer = Math.random() * 200; // Delay before next spawn
                }
            } else {
                // Countdown to respawn
                meteor.resetTimer--;
                if (meteor.resetTimer <= 0) {
                    meteor.active = true;
                    meteor.position.set(
                        60,
                        (Math.random() - 0.5) * 50,
                        (Math.random() - 0.5) * 40 - 20
                    );
                }
            }
        });

        // Update geometry
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        // We can't easily do per-vertex alpha with basic line material easily without shader, 
        // so we'll just stick to geometry updates for now and uniform alpha.
        // For a better effect, we'd use a shader material.
    });

    return (
        <lineSegments ref={lineRef} geometry={geometry}>
            <lineBasicMaterial
                color="#ffffff"
                transparent
                opacity={0.6}
                blending={THREE.AdditiveBlending}
            />
        </lineSegments>
    );
}
