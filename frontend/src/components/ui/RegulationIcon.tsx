/**
 * RegulationIcon.tsx
 * 
 * A custom SVG icon for the Regulation Agent / Compliance feature.
 * Design: Document/scroll with a checkmark representing regulatory compliance.
 */

import { cn } from '@/lib/utils';

interface RegulationIconProps {
    className?: string;
    size?: number;
}

export const RegulationIcon = ({ className, size = 20 }: RegulationIconProps) => {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className={cn("shrink-0", className)}
        >
            {/* Document/Scroll base */}
            <path
                d="M6 2C4.89543 2 4 2.89543 4 4V20C4 21.1046 4.89543 22 6 22H18C19.1046 22 20 21.1046 20 20V8L14 2H6Z"
                fill="currentColor"
                fillOpacity="0.15"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
            />

            {/* Document fold */}
            <path
                d="M14 2V6C14 7.10457 14.8954 8 16 8H20"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
            />

            {/* Checkmark */}
            <path
                d="M9 13L11 15L15 11"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
            />

            {/* Horizontal lines representing text */}
            <path
                d="M8 18H12"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                opacity="0.5"
            />
        </svg>
    );
};
