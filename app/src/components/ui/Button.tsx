import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "accent" | "ghost" | "outline";

const styles: Record<Variant, string> = {
  primary:
    "bg-pine text-on-pine hover:bg-pine-deep active:scale-[0.98] shadow-card",
  accent:
    "bg-amber text-on-amber hover:bg-amber-deep active:scale-[0.98] shadow-card",
  ghost: "text-pine hover:bg-pine-soft",
  outline: "border border-line-strong text-ink hover:border-pine hover:text-pine bg-surface",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "md" | "lg";
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`inline-flex cursor-pointer items-center justify-center gap-2 rounded-full font-semibold transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-45 ${
        size === "lg" ? "min-h-12 px-7 py-3 text-base" : "min-h-11 px-5 py-2.5 text-sm"
      } ${styles[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
