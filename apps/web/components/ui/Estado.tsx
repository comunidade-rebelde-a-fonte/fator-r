import type { ReactNode } from "react";

export function Carregando({ texto = "Carregando..." }: { texto?: string }) {
  return (
    <p role="status" className="py-6 text-sm text-zinc-500">
      {texto}
    </p>
  );
}

export function Vazio({ children }: { children: ReactNode }) {
  return (
    <div className="rounded border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-500">
      {children}
    </div>
  );
}

export function Erro({ texto, onRetry }: { texto: string; onRetry?: () => void }) {
  return (
    <div
      data-testid="estado-erro"
      className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-800"
    >
      {texto}{" "}
      {onRetry && (
        <button type="button" className="underline" onClick={onRetry}>
          Tentar de novo
        </button>
      )}
    </div>
  );
}
