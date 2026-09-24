import type { ButtonHTMLAttributes } from "react";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-[4px] border font-bold tracking-[.055em] uppercase transition-colors disabled:cursor-not-allowed disabled:opacity-60";

// Primário: texto escuro sobre laranja sólido (8,42:1). O gradiente do ceath com texto branco falha no AA.
const VARIANTES = {
  primario: "border-accent bg-accent text-on-accent hover:bg-accent-soft",
  secundario: "border-accent/65 bg-accent/5 text-fg hover:bg-accent/12",
  fantasma: "border-line-strong text-fg hover:bg-panel-2",
  perigo: "border-danger/60 text-danger-soft hover:bg-danger/10",
} as const;

const TAMANHOS = {
  sm: "px-2 py-1 text-[11px]",
  md: "px-3 py-1.5 text-xs",
  lg: "px-4 py-2 text-xs",
} as const;

export type VarianteBotao = keyof typeof VARIANTES;
export type TamanhoBotao = keyof typeof TAMANHOS;

/** Classes do botão, para `<Link>` e `<label>` que precisam parecer botão. */
export function classesBotao(
  variante: VarianteBotao = "primario",
  tamanho: TamanhoBotao = "md",
  extra = "",
): string {
  return `${BASE} ${VARIANTES[variante]} ${TAMANHOS[tamanho]} ${extra}`.trim();
}

export function Botao({
  variante = "primario",
  tamanho = "md",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: VarianteBotao; tamanho?: TamanhoBotao }) {
  return <button type={type} className={classesBotao(variante, tamanho, className)} {...props} />;
}
