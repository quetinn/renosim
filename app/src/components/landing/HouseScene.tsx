import { motion, useReducedMotion } from "motion/react";

const DPE_COLORS: Record<string, string> = {
  A: "var(--color-dpe-a)",
  B: "var(--color-dpe-b)",
  C: "var(--color-dpe-c)",
  D: "var(--color-dpe-d)",
  E: "var(--color-dpe-e)",
  F: "var(--color-dpe-f)",
  G: "var(--color-dpe-g)",
};

/**
 * Animated hero illustration: a house losing heat, a DPE ladder beside it and
 * a cursor sliding from F to B. Pure SVG + CSS keyframes (gated behind
 * prefers-reduced-motion in index.css).
 */
export function HouseScene() {
  const reduced = useReducedMotion();
  const classes = ["A", "B", "C", "D", "E", "F", "G"];

  return (
    <svg
      viewBox="0 0 560 430"
      role="img"
      aria-label="Illustration : une maison dont l'étiquette énergie passe de F à B après rénovation"
      className="h-auto w-full max-w-xl"
    >
      {/* ground */}
      <ellipse cx="250" cy="392" rx="238" ry="26" fill="var(--color-pine-soft)" />

      {/* sun */}
      <g className="animate-float-slow" style={{ transformOrigin: "88px 84px" }}>
        <circle cx="88" cy="84" r="30" fill="var(--color-amber-soft)" />
        <circle cx="88" cy="84" r="19" fill="var(--color-amber)" opacity="0.9" />
      </g>

      {/* tree */}
      <g>
        <rect x="428" y="330" width="10" height="44" rx="4" fill="#8a6a4b" />
        <circle cx="433" cy="308" r="34" fill="var(--color-pine)" opacity="0.85" />
        <circle cx="414" cy="326" r="22" fill="var(--color-pine-deep)" opacity="0.8" />
      </g>

      {/* heat particles escaping the roof */}
      {!reduced &&
        [0, 1, 2, 3].map((i) => (
          <circle
            key={i}
            cx={190 + i * 34}
            cy={140}
            r={i % 2 === 0 ? 5 : 4}
            fill="var(--color-amber)"
            opacity="0"
            className="animate-heat-rise"
            style={{ animationDelay: `${i * 0.7}s` }}
          />
        ))}

      {/* house */}
      <g>
        {/* body */}
        <rect x="140" y="216" width="220" height="160" rx="10" fill="#fffdf8" stroke="var(--color-line-strong)" strokeWidth="2.5" />
        {/* roof */}
        <path d="M124 222 L250 132 L376 222 Z" fill="var(--color-pine)" />
        <path d="M124 222 L250 132 L376 222" fill="none" stroke="var(--color-pine-deep)" strokeWidth="3" strokeLinejoin="round" />
        {/* chimney */}
        <rect x="312" y="152" width="24" height="52" rx="4" fill="var(--color-clay)" />
        {/* door */}
        <rect x="236" y="296" width="42" height="80" rx="6" fill="var(--color-pine-deep)" />
        <circle cx="268" cy="338" r="3" fill="var(--color-amber)" />
        {/* windows */}
        <g fill="#cfe3ff" stroke="var(--color-line-strong)" strokeWidth="2">
          <rect x="164" y="248" width="46" height="46" rx="6" />
          <rect x="296" y="248" width="46" height="46" rx="6" />
        </g>
        <g stroke="var(--color-line-strong)" strokeWidth="1.6">
          <line x1="187" y1="250" x2="187" y2="292" />
          <line x1="166" y1="271" x2="208" y2="271" />
          <line x1="319" y1="250" x2="319" y2="292" />
          <line x1="298" y1="271" x2="340" y2="271" />
        </g>
        {/* insulation layer being wrapped (dashed outline) */}
        <rect
          x="131"
          y="207"
          width="238"
          height="178"
          rx="14"
          fill="none"
          stroke="var(--color-amber)"
          strokeWidth="2.5"
          strokeDasharray="10 14"
          className="animate-dash-flow"
        />
      </g>

      {/* DPE ladder */}
      <g aria-hidden="true">
        {classes.map((cls, i) => {
          const width = 44 + i * 8;
          return (
            <g key={cls} transform={`translate(452, ${118 + i * 34})`}>
              <path
                d={`M0 4 Q0 0 4 0 H${width} L${width + 13} 13 L${width} 26 H4 Q0 26 0 22 Z`}
                fill={DPE_COLORS[cls]}
                opacity={cls === "B" || cls === "F" ? 1 : 0.35}
              />
              <text
                x="12"
                y="18"
                fontSize="15"
                fontWeight="700"
                fill={cls === "D" || cls === "C" ? "#4b5b50" : "#fff"}
              >
                {cls}
              </text>
            </g>
          );
        })}
        {/* cursor sliding from F (index 5) to B (index 1) */}
        <motion.g
          initial={{ y: 118 + 5 * 34 }}
          animate={{ y: 118 + 1 * 34 }}
          transition={
            reduced
              ? { duration: 0 }
              : { delay: 1.2, duration: 1.6, ease: [0.3, 0.9, 0.3, 1] }
          }
        >
          <path d="M446 13 L432 3 V23 Z" fill="var(--color-ink)" />
        </motion.g>
      </g>
    </svg>
  );
}
