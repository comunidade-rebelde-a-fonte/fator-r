/** Aviso permanente de conformidade (PRD §8, CLAUDE.md §3.14). Componente único. */
export const DISCLAIMER_TEXTO =
  "Esta plataforma não é a apuração oficial. O PGDAS-D da Receita Federal prevalece.";

export function Disclaimer() {
  return (
    <footer
      role="contentinfo"
      data-testid="disclaimer-pgdas"
      className="sticky bottom-0 border-t border-amber-300 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900"
    >
      {DISCLAIMER_TEXTO}
    </footer>
  );
}
