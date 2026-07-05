import { HelpCircle } from "lucide-react";

/**
 * Contextual help attached to a form field. Native <details> keeps it
 * keyboard- and screen-reader-friendly without extra ARIA wiring.
 */
export function InfoTip({ text }: { text: string }) {
  return (
    <details className="group relative inline-block align-middle">
      <summary
        className="inline-flex min-h-6 min-w-6 cursor-pointer list-none items-center justify-center rounded-full text-ink-faint transition-colors hover:text-pine [&::-webkit-details-marker]:hidden"
        aria-label="Aide"
      >
        <HelpCircle size={16} aria-hidden />
      </summary>
      <div
        role="note"
        className="absolute left-1/2 z-30 mt-2 w-64 -translate-x-1/2 rounded-xl border border-line bg-surface p-3 text-xs leading-relaxed text-ink-soft shadow-lift"
      >
        {text}
      </div>
    </details>
  );
}
