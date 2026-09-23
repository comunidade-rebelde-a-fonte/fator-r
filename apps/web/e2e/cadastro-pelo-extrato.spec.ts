/**
 * M8 — cadastro de empresa pelo extrato (T-806): AT-001, AT-003, AT-011 e AT-012 pela interface.
 * Roda junto do aceite da v1 (make e2e), em ambiente limpo e sem chamada externa.
 */
import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

import { API, DISCLAIMER, EXTRATO_PADRAO, SAIDA, cnpj, entrar, formatarCnpj } from "./apoio";

test.describe.configure({ mode: "serial" });

const suf = Date.now().toString().slice(-6);
let page: Page;

test.beforeAll(async ({ browser }) => {
  page = await browser.newPage();
  await entrar(page);
});

test.afterAll(async () => {
  await page.close();
});

/** Extrato padrão (PA 09/2026, RPA 50.000,00, "CLINICA EXEMPLO LTDA") com outro CNPJ. */
async function enviarExtrato(cnpjEmpresa: string): Promise<void> {
  fs.mkdirSync(SAIDA, { recursive: true });
  const arquivo = path.join(SAIDA, `extrato-cadastro-${cnpjEmpresa}.txt`);
  fs.writeFileSync(
    arquivo,
    EXTRATO_PADRAO.replaceAll("11.222.333/0001-81", formatarCnpj(cnpjEmpresa)),
  );
  await page.goto("/inbox");
  await page.locator("input[name=arquivo]").setInputFiles(arquivo);
}

async function empresaPorCnpj(cnpjEmpresa: string): Promise<{ id: string; nome: string }[]> {
  const r = await page.request.get(`${API}/companies?busca=${cnpjEmpresa}`);
  return (await r.json()).items;
}

test("M8 CNPJ fora da carteira: cadastrar e vincular em 2 cliques, com receita do PA", async () => {
  const novo = cnpj(`81${suf}0001`);
  await enviarExtrato(novo);

  const bloco = page.getByTestId("cadastro-pelo-extrato");
  await expect(bloco).toContainText(formatarCnpj(novo), { timeout: 30_000 });
  await expect(page.getByTestId("resultado-upload")).toContainText("cnpj_nao_encontrado");
  await expect(page.getByText(DISCLAIMER).first()).toBeVisible();
  expect(await empresaPorCnpj(novo)).toHaveLength(0); // nada gravado sem confirmação

  await bloco.getByRole("button", { name: "Cadastrar e vincular" }).click(); // 1º clique
  const campoCnpj = bloco.locator("input[name=cnpj]");
  await expect(campoCnpj).toHaveValue(formatarCnpj(novo));
  await expect(campoCnpj).toHaveJSProperty("readOnly", true);
  await expect(bloco.getByLabel("Nome", { exact: true })).toHaveValue("CLINICA EXEMPLO LTDA");
  await expect(bloco.getByRole("radio", { name: "Sim" })).toBeChecked();
  await bloco.getByRole("button", { name: "Confirmar cadastro e vínculo" }).click(); // 2º clique

  await expect(page.getByTestId("resultado-upload")).toContainText(
    "cadastrada a partir do extrato",
    { timeout: 30_000 },
  );
  await expect(page.getByTestId("cadastro-pelo-extrato")).toHaveCount(0);

  const [empresa] = await empresaPorCnpj(novo);
  expect(empresa.nome).toBe("CLINICA EXEMPLO LTDA");
  const movimentos = await (
    await page.request.get(`${API}/companies/${empresa.id}/movements`)
  ).json();
  expect(
    movimentos.map((m: { competencia: string; receita_bruta: string; origem: string }) => [
      m.competencia,
      m.receita_bruta,
      m.origem,
    ]),
  ).toEqual([["2026-09", "50000.00", "pgdas"]]);

  const documento = (
    await (await page.request.get(`${API}/inbox?status=linked`)).json()
  ).items.find((d: { company_id: string | null }) => d.company_id === empresa.id);
  const trace = await (await page.request.get(`${API}/traces/${documento.trace_id}`)).json();
  expect(trace.trace.gatilho).toBe("cadastro_pelo_extrato");
  expect(trace.trace.company_id).toBe(empresa.id);
  expect(trace.decisao.empresa_criada).toBe(true);
});

test("M8 CNPJ cadastrado por outra pessoa no meio do caminho: oferece vincular", async () => {
  const concorrente = cnpj(`82${suf}0001`);
  await enviarExtrato(concorrente);
  const bloco = page.getByTestId("cadastro-pelo-extrato");
  await expect(bloco).toContainText(formatarCnpj(concorrente), { timeout: 30_000 });
  await bloco.getByRole("button", { name: "Cadastrar e vincular" }).click();

  const criada = await page.request.post(`${API}/companies`, {
    data: { nome: "Cadastrada por outro analista", cnpj: concorrente, sujeita_fator_r: true },
  });
  expect(criada.status()).toBe(201);

  await bloco.getByRole("button", { name: "Confirmar cadastro e vínculo" }).click();
  await expect(bloco.getByRole("alert")).toContainText("Já existe uma empresa com esse CNPJ");
  await bloco.getByRole("button", { name: "Vincular à empresa já cadastrada" }).click();
  await expect(page.getByTestId("resultado-upload")).toContainText(
    "Extrato vinculado a Cadastrada por outro analista",
    { timeout: 30_000 },
  );
  expect(await empresaPorCnpj(concorrente)).toHaveLength(1);
});

test("M8 detalhe do documento mostra o nome lido e o mesmo bloco de cadastro", async () => {
  const outro = cnpj(`83${suf}0001`);
  await enviarExtrato(outro);
  await expect(page.getByTestId("cadastro-pelo-extrato")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("resultado-upload").getByRole("link", { name: "ver documento" }).click();
  await expect(page.getByTestId("nome-empresarial")).toContainText("CLINICA EXEMPLO LTDA");
  await expect(page.getByTestId("cadastro-pelo-extrato")).toContainText(formatarCnpj(outro));
  await expect(page.getByText(DISCLAIMER).first()).toBeVisible();
});
