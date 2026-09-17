import type { ReactNode } from "react";

const CORES = {
  cinza: "bg-zinc-100 text-zinc-700",
  azul: "bg-sky-100 text-sky-800",
  verde: "bg-emerald-100 text-emerald-800",
  amarelo: "bg-amber-100 text-amber-900",
  vermelho: "bg-red-100 text-red-800",
  roxo: "bg-violet-100 text-violet-800",
} as const;

export type CorBadge = keyof typeof CORES;

export function Badge({ cor = "cinza", children }: { cor?: CorBadge; children: ReactNode }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${CORES[cor]}`}>
      {children}
    </span>
  );
}
