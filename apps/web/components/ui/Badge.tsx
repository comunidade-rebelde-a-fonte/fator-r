import type { ReactNode } from "react";

// Selo translúcido com borda, sempre com texto: não se confunde com o botão primário sólido.
const CORES = {
  cinza: "border-line-strong/60 bg-fg/5 text-muted",
  azul: "border-info/40 bg-info/12 text-info",
  verde: "border-ok/40 bg-ok/12 text-ok",
  amarelo: "border-accent/50 bg-accent/12 text-accent",
  vermelho: "border-danger/50 bg-danger/12 text-danger-soft",
  roxo: "border-extra/40 bg-extra/12 text-extra",
} as const;

export type CorBadge = keyof typeof CORES;

export function Badge({ cor = "cinza", children }: { cor?: CorBadge; children: ReactNode }) {
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 align-middle font-sans text-xs font-medium tracking-normal normal-case ${CORES[cor]}`}
    >
      {children}
    </span>
  );
}
