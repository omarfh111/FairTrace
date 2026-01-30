/**
 * StarFieldBackground.tsx
 * 
 * A subtle, continuous space-themed animated background for the FairTrace application.
 * Creates a multi-layered parallax effect with twinkling stars, faint orbital rings,
 * and rare shooting stars.
 * 
 * Performance optimized:
 * - Canvas-based star rendering (no DOM overhead)
 * - Throttled to 30fps (sufficient for subtle background)
 * - Pauses when tab is hidden
 * - Respects prefers-reduced-motion
 */

import { useRef, useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';

interface Star {
    x: number;
    y: number;
    size: number;
    baseOpacity: number;
    twinkleSpeed: number;
    twinklePhase: number;
    layer: 1 | 2 | 3;
}

interface ShootingStar {
    x: number;
    y: number;
    angle: number;
    length: number;
    opacity: number;
}

// Deep space color palette
const COLORS = {
    deepSpace1: '#0A0E27',
    deepSpace2: '#1A1F3A',
    deepSpace3: '#1E2139',
    starWhite: '#FFFFFF',
    starBlue: '#E0E7FF',
    starPurple: '#F3F0FF',
    nebulaGlow: 'rgba(139, 127, 255, 0.03)',
};

export const StarFieldBackground = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animationRef = useRef<number | null>(null);
    const isVisibleRef = useRef(true);
    const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
    const [shootingStar, setShootingStar] = useState<ShootingStar | null>(null);

    // Check for reduced motion preference
    useEffect(() => {
        const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
        setPrefersReducedMotion(mediaQuery.matches);

        const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
        mediaQuery.addEventListener('change', handler);
        return () => mediaQuery.removeEventListener('change', handler);
    }, []);

    // Generate stars once
    const stars = useMemo<Star[]>(() => {
        const result: Star[] = [];
        const count = 120;

        for (let i = 0; i < count; i++) {
            const layer = i < 50 ? 1 : i < 90 ? 2 : 3;
            result.push({
                x: Math.random(),
                y: Math.random(),
                size: layer === 1 ? 0.8 : layer === 2 ? 1.2 : 1.8,
                baseOpacity: layer === 1 ? 0.3 : layer === 2 ? 0.5 : 0.7,
                twinkleSpeed: 2000 + Math.random() * 6000, // 2-8 seconds in ms
                twinklePhase: Math.random() * Math.PI * 2,
                layer,
            });
        }
        return result;
    }, []);

    // Handle canvas resize
    useEffect(() => {
        const handleResize = () => {
            const canvas = canvasRef.current;
            if (!canvas) return;

            const dpr = window.devicePixelRatio || 1;
            canvas.width = window.innerWidth * dpr;
            canvas.height = window.innerHeight * dpr;
            canvas.style.width = `${window.innerWidth}px`;
            canvas.style.height = `${window.innerHeight}px`;
        };

        handleResize();
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Visibility change handler
    useEffect(() => {
        const handleVisibilityChange = () => {
            isVisibleRef.current = !document.hidden;
        };
        document.addEventListener('visibilitychange', handleVisibilityChange);
        return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
    }, []);

    // Canvas animation loop
    useEffect(() => {
        if (prefersReducedMotion) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let lastTime = 0;
        const frameInterval = 33; // ~30fps

        const animate = (timestamp: number) => {
            if (!isVisibleRef.current) {
                animationRef.current = requestAnimationFrame(animate);
                return;
            }

            // Throttle
            if (timestamp - lastTime < frameInterval) {
                animationRef.current = requestAnimationFrame(animate);
                return;
            }
            lastTime = timestamp;

            const { width, height } = canvas;

            // Clear
            ctx.clearRect(0, 0, width, height);

            // Draw stars with twinkling
            stars.forEach(star => {
                // Calculate twinkle using sine wave
                const twinkle = Math.sin((timestamp / star.twinkleSpeed) * Math.PI * 2 + star.twinklePhase);
                const opacity = star.baseOpacity * (0.5 + 0.5 * twinkle);

                // Star color based on layer
                const color = star.layer === 1 ? COLORS.starBlue :
                    star.layer === 2 ? COLORS.starWhite :
                        COLORS.starPurple;

                ctx.beginPath();
                ctx.arc(
                    star.x * width,
                    star.y * height,
                    star.size * (window.devicePixelRatio || 1),
                    0,
                    Math.PI * 2
                );
                ctx.fillStyle = color;
                ctx.globalAlpha = opacity;
                ctx.fill();
            });

            ctx.globalAlpha = 1;
            animationRef.current = requestAnimationFrame(animate);
        };

        // Start animation
        animationRef.current = requestAnimationFrame(animate);

        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [stars, prefersReducedMotion]);

    // Shooting star timer
    useEffect(() => {
        if (prefersReducedMotion) return;

        const triggerShootingStar = () => {
            setShootingStar({
                x: Math.random() * 0.6,
                y: Math.random() * 0.3,
                angle: -35 - Math.random() * 25,
                length: 100 + Math.random() * 50,
                opacity: 0.7 + Math.random() * 0.3,
            });

            setTimeout(() => setShootingStar(null), 700);
        };

        // Schedule shooting stars
        const scheduleNext = () => {
            const delay = 30000 + Math.random() * 30000; // 30-60s
            return window.setTimeout(() => {
                triggerShootingStar();
                timerId = scheduleNext();
            }, delay);
        };

        // First one after 8-15s
        let timerId = window.setTimeout(() => {
            triggerShootingStar();
            timerId = scheduleNext();
        }, 8000 + Math.random() * 7000);

        return () => clearTimeout(timerId);
    }, [prefersReducedMotion]);

    // Static fallback for reduced motion
    if (prefersReducedMotion) {
        return (
            <div
                className="fixed inset-0 z-0 pointer-events-none"
                style={{
                    background: `linear-gradient(180deg, ${COLORS.deepSpace1} 0%, ${COLORS.deepSpace2} 50%, ${COLORS.deepSpace3} 100%)`,
                }}
            />
        );
    }

    return (
        <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
            {/* Layer 1: Deep space gradient */}
            <div
                className="absolute inset-0"
                style={{
                    background: `radial-gradient(ellipse at 50% 0%, ${COLORS.deepSpace2} 0%, ${COLORS.deepSpace1} 50%, #050810 100%)`,
                }}
            />

            {/* Layer 2: Subtle nebula glow */}
            <div
                className="absolute inset-0 opacity-40"
                style={{
                    background: `radial-gradient(ellipse at 20% 80%, rgba(139, 127, 255, 0.04) 0%, transparent 40%),
                       radial-gradient(ellipse at 80% 20%, rgba(0, 200, 150, 0.03) 0%, transparent 40%)`,
                }}
            />

            {/* Layer 3: Canvas stars */}
            <canvas
                ref={canvasRef}
                className="absolute inset-0"
            />

            {/* Layer 4: Subtle orbital ring */}
            <motion.div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                style={{
                    width: '160vmax',
                    height: '160vmax',
                }}
                animate={{ rotate: 360 }}
                transition={{
                    duration: 180,
                    repeat: Infinity,
                    ease: 'linear',
                }}
            >
                <div
                    className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
                    style={{
                        width: '70%',
                        height: '25%',
                        border: '1px solid rgba(139, 127, 255, 0.06)',
                    }}
                />
                <div
                    className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
                    style={{
                        width: '90%',
                        height: '35%',
                        border: '1px solid rgba(100, 150, 255, 0.03)',
                    }}
                />
            </motion.div>

            {/* Layer 5: Shooting star */}
            {shootingStar && (
                <motion.div
                    className="absolute pointer-events-none"
                    style={{
                        left: `${shootingStar.x * 100}%`,
                        top: `${shootingStar.y * 100}%`,
                        width: shootingStar.length,
                        height: 2,
                        background: `linear-gradient(90deg, transparent 0%, rgba(255,255,255,${shootingStar.opacity * 0.5}) 30%, rgba(255,255,255,${shootingStar.opacity}) 100%)`,
                        transformOrigin: 'right center',
                        transform: `rotate(${shootingStar.angle}deg)`,
                        boxShadow: '0 0 6px rgba(255,255,255,0.5)',
                    }}
                    initial={{ opacity: 0, scaleX: 0, x: 0, y: 0 }}
                    animate={{
                        opacity: [0, 1, 1, 0],
                        scaleX: [0, 1, 1, 0.5],
                        x: [0, -250],
                        y: [0, 120],
                    }}
                    transition={{
                        duration: 0.6,
                        ease: 'easeOut',
                        times: [0, 0.1, 0.7, 1],
                    }}
                />
            )}
        </div>
    );
};
