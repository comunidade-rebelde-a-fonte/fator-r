import fs from "node:fs";
import path from "node:path";
import { expect, type APIRequestContext, type Page } from "@playwright/test";

// O Playwright roda a partir de apps/web (make e2e).
const aqui = path.resolve(process.cwd(), "e2e");
const raiz = path.resolve(process.cwd(), "../..");

function lerEnv(arquivo: string): Record<string, string> {
  return Object.fromEntries(
    fs
      .readFileSync(arquivo, "utf8")
      .split("\n")
      .filter((l) => l.includes("=") && !l.trimStart().startsWith("#"))
      .map((l) => {
        const i = l.indexOf("=");
        return [
          l.slice(0, i).trim(),
          l
            .slice(i + 1)
            .trim()
            .replace(/^['"]|['"]$/g, ""),
        ];
      }),
  );
}

export const env = lerEnv(path.join(raiz, ".env"));
export const API = process.env.E2E_API_URL ?? env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const DISCLAIMER = "O PGDAS-D da Receita Federal prevalece.";
export const SAIDA = path.join(aqui, ".saida");
export const EXTRATO_PADRAO = fs.readFileSync(
  path.join(raiz, "apps/api/fixtures/pgdas/txt_padrao/documento.txt"),
  "utf8",
);

export const MESES = [
  "2025-09",
  "2025-10",
  "2025-11",
  "2025-12",
  "2026-01",
  "2026-02",
  "2026-03",
  "2026-04",
  "2026-05",
  "2026-06",
  "2026-07",
  "2026-08",
];

export function cnpj(base12: string): string {
  const dv = (n: string, p: number[]) => {
    const r = n.split("").reduce((s, x, i) => s + Number(x) * p[i], 0) % 11;
    return r < 2 ? "0" : String(11 - r);
  };
  const d1 = dv(base12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  return base12 + d1 + dv(base12 + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
}

export const formatarCnpj = (c: string) =>
  `${c.slice(0, 2)}.${c.slice(2, 5)}.${c.slice(5, 8)}/${c.slice(8, 12)}-${c.slice(12)}`;

export const semNbsp = (t: string | null) => (t ?? "").replace(/ /g, " ").trim();

export async function entrar(page: Page): Promise<void> {
  await page.goto("/login");
  await page.fill("input[name=email]", env.SEED_USER_EMAIL);
  await page.fill("input[name=senha]", env.SEED_USER_PASSWORD);
  await page.click("button[type=submit]");
  await page.waitForURL("**/carteira");
}

export async function lancar(
  request: APIRequestContext,
  companyId: string,
  valores: Record<string, string>,
  meses = MESES,
): Promise<void> {
  for (const mes of meses) {
    const r = await request.put(`${API}/companies/${companyId}/movements/${mes}`, {
      data: valores,
    });
    expect(r.status()).toBe(200);
  }
}

export function registrarTrace(nome: string, traceId: string): void {
  fs.mkdirSync(SAIDA, { recursive: true });
  const arquivo = path.join(SAIDA, "traces.json");
  const atual = fs.existsSync(arquivo) ? JSON.parse(fs.readFileSync(arquivo, "utf8")) : {};
  fs.writeFileSync(arquivo, JSON.stringify({ ...atual, [nome]: traceId }, null, 2));
}
