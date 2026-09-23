import type { ReactNode } from "react";

/** `h1` da página em Oswald maiúsculo (só CSS: o texto e o nome acessível não mudam). */
export function TituloPagina({ children, acoes }: { children: ReactNode; acoes?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <h1 className="font-display text-3xl leading-none tracking-[-.01em] uppercase">{children}</h1>
      {acoes}
    </div>
  );
}
