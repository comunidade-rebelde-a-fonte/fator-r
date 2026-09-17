/** Máscara e checagem de CNPJ para feedback imediato. A api valida de novo. */

export function mascararCnpj(valor: string): string {
  const d = valor.replace(/\D/g, "").slice(0, 14);
  return d
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d)/, "$1-$2");
}

function digito(numeros: string, pesos: number[]): string {
  const resto = numeros.split("").reduce((s, n, i) => s + Number(n) * pesos[i], 0) % 11;
  return resto < 2 ? "0" : String(11 - resto);
}

export function cnpjValido(valor: string): boolean {
  const d = valor.replace(/\D/g, "");
  if (d.length !== 14 || new Set(d).size === 1) return false;
  const dv1 = digito(d.slice(0, 12), [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  const dv2 = digito(d.slice(0, 12) + dv1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  return d.slice(12) === dv1 + dv2;
}
