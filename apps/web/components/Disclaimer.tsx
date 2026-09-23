/** Aviso permanente de conformidade (PRD §8, CLAUDE.md §3.14). Componente único. */
export const DISCLAIMER_TEXTO =
  "Esta plataforma não é a apuração oficial. O PGDAS-D da Receita Federal prevalece.";

export function Disclaimer() {
  return (
    <footer
      role="contentinfo"
      data-testid="disclaimer-pgdas"
      className="border-accent/60 bg-panel text-fg sticky bottom-0 border-t px-4 py-2 text-center text-xs"
    >
      {DISCLAIMER_TEXTO}
    </footer>
  );
}
