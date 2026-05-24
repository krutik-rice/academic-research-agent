"use client";
import React from "react";

// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ children, className = "" }: Readonly<{ children: React.ReactNode; className?: string }>) {
  return (
    <div
      className={`rounded-xl p-4 border ${className}`}
      style={{ backgroundColor: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      {children}
    </div>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────────
const BADGE_COLORS: Record<string, string> = {
  arxiv:   "rgba(185,28,28,0.25)",
  scholar: "rgba(37,99,235,0.25)",
  s2:      "rgba(67,56,202,0.25)",
  done:    "rgba(129,201,149,0.2)",
  pending: "rgba(253,214,99,0.2)",
  danger:  "rgba(242,139,130,0.2)",
};

export function Badge({ label, variant = "arxiv" }: Readonly<{ label: string; variant?: string }>) {
  const bg = BADGE_COLORS[variant] ?? "rgba(138,180,248,0.15)";
  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-xs font-medium"
      style={{ backgroundColor: bg, color: "var(--color-text)" }}
    >
      {label}
    </span>
  );
}

// ── Button ────────────────────────────────────────────────────────────────────
interface BtnProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger";
  loading?: boolean;
}
export function Btn({ children, variant = "primary", loading, className = "", ...rest }: Readonly<BtnProps>) {
  const styles: Record<string, React.CSSProperties> = {
    primary: { backgroundColor: "var(--color-accent2)", color: "#fff", border: "none" },
    ghost:   { backgroundColor: "transparent", color: "var(--color-accent)", border: "1px solid var(--color-accent)" },
    danger:  { backgroundColor: "transparent", color: "var(--color-danger)", border: "1px solid var(--color-danger)" },
  };
  return (
    <button
      {...rest}
      disabled={rest.disabled ?? loading}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-opacity disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed ${className}`}
      style={styles[variant]}
    >
      {loading ? "…" : children}
    </button>
  );
}

// ── Input ─────────────────────────────────────────────────────────────────────
export function Input(props: Readonly<React.InputHTMLAttributes<HTMLInputElement>>) {
  return (
    <input
      {...props}
      className={`w-full px-3 py-2 rounded-lg text-sm outline-none border focus:ring-1 ${props.className ?? ""}`}
      style={{
        backgroundColor: "var(--color-surface2)",
        color: "var(--color-text)",
        borderColor: "var(--color-border)",
        // @ts-expect-error css vars
        "--tw-ring-color": "var(--color-accent)",
      }}
    />
  );
}

// ── Select ────────────────────────────────────────────────────────────────────
export function Select(props: Readonly<React.SelectHTMLAttributes<HTMLSelectElement>>) {
  return (
    <select
      {...props}
      className={`px-3 py-2 rounded-lg text-sm outline-none border ${props.className ?? ""}`}
      style={{
        backgroundColor: "var(--color-surface2)",
        color: "var(--color-text)",
        borderColor: "var(--color-border)",
      }}
    />
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────────
export function ProgressBar({ value, className = "" }: Readonly<{ value: number; className?: string }>) {
  return (
    <div className={`h-1.5 rounded-full overflow-hidden ${className}`} style={{ backgroundColor: "var(--color-surface2)" }}>
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${Math.min(100, Math.max(0, value * 100))}%`, backgroundColor: "var(--color-accent)" }}
      />
    </div>
  );
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner() {
  return (
    <div
      className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin inline-block"
      style={{ borderColor: "var(--color-accent)", borderTopColor: "transparent" }}
    />
  );
}

// ── Section heading ───────────────────────────────────────────────────────────
export function H2({ children }: Readonly<{ children: React.ReactNode }>) {
  return <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--color-text)" }}>{children}</h2>;
}

// ── Error / info banners ──────────────────────────────────────────────────────
export function ErrorBanner({ message }: Readonly<{ message: string }>) {
  return (
    <div className="rounded-lg px-4 py-3 text-sm" style={{ backgroundColor: "rgba(242,139,130,0.15)", color: "var(--color-danger)" }}>
      {message}
    </div>
  );
}

export function InfoBanner({ message }: Readonly<{ message: string }>) {
  return (
    <div className="rounded-lg px-4 py-3 text-sm" style={{ backgroundColor: "rgba(138,180,248,0.1)", color: "var(--color-muted)" }}>
      {message}
    </div>
  );
}
