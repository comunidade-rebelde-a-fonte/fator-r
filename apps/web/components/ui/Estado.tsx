import type { ReactNode } from "react";

export function Carregando({ texto = "Carregando..." }: { texto?: string }) {
  return (
    <p role="status" className="text-muted py-6 text-sm">
      {texto}
    </p>
  );
}

export function Vazio({ children }: { children: ReactNode }) {
  return (
    <div className="border-line-strong/60 text-muted rounded-[10px] border border-dashed p-6 text-center text-sm">
      {children}
    </div>
  );
}

export function Erro({ texto, onRetry }: { texto: string; onRetry?: () => void }) {
  return (
    <div
      data-testid="estado-erro"
      className="border-danger/50 bg-danger/12 text-danger-soft rounded-[10px] border p-4 text-sm"
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
