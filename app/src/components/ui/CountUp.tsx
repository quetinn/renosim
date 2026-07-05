import { animate, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

/** Animated counter for the landing stats; renders the final value directly
 *  when the user prefers reduced motion. */
export function CountUp({
  value,
  format = (v: number) => new Intl.NumberFormat("fr-FR").format(Math.round(v)),
  duration = 1.6,
}: {
  value: number;
  format?: (value: number) => string;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(reduced ? format(value) : format(0));

  useEffect(() => {
    if (!inView) return;
    if (reduced) {
      setDisplay(format(value));
      return;
    }
    const controls = animate(0, value, {
      duration,
      ease: [0.16, 0.8, 0.3, 1],
      onUpdate: (v) => setDisplay(format(v)),
    });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView, value, reduced]);

  return (
    <span ref={ref} className="tabular">
      {display}
    </span>
  );
}
