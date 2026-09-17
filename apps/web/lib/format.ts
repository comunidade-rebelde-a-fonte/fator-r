/** Formatação pt-BR. Só apresenta valores que vêm da API; nenhum cálculo tributário aqui. */

const reais = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const percentual = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatarReais(valor: string | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  return reais.format(Number(valor));
}

export function formatarPercentual(valor: string | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  return percentual.format(Number(valor));
}

/** "1.234,56" ou "1234.56" → "1234.56". Devolve null se não for um valor monetário válido. */
export function valorBRParaDecimal(entrada: string): string | null {
  const limpo = entrada.trim().replace(/\s|R\$/g, "");
  if (limpo === "") return "0.00";
  const normalizado = limpo.includes(",") ? limpo.replace(/\./g, "").replace(",", ".") : limpo;
  if (!/^\d+(\.\d{1,2})?$/.test(normalizado)) return null;
  const [inteiro, centavos = ""] = normalizado.split(".");
  return `${inteiro}.${centavos.padEnd(2, "0")}`;
}

export function decimalParaEntradaBR(valor: string | null | undefined): string {
  if (!valor) return "";
  return Number(valor).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export function rotuloCompetencia(competencia: string): string {
  const [ano, mes] = competencia.split("-");
  return `${MESES[Number(mes) - 1]}/${ano}`;
}

/** Aritmética de calendário em "YYYY-MM" (navegação de telas). */
export function somarMeses(competencia: string, meses: number): string {
  const [ano, mes] = competencia.split("-").map(Number);
  const indice = ano * 12 + (mes - 1) + meses;
  return `${Math.floor(indice / 12)}-${String((indice % 12) + 1).padStart(2, "0")}`;
}

export function competenciaAtual(hoje = new Date()): string {
  return `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}`;
}
