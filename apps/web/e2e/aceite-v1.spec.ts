/**
 * Aceite da v1: um teste por item da PRD §13 (T-705).
 * Roda em ambiente limpo (make e2e), com LLM_PROVIDER=fake: nenhuma chamada externa.
 */
import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

import {
  API,
  DISCLAIMER,
  EXTRATO_PADRAO,
  MESES,
  SAIDA,
  cnpj,
  entrar,
  formatarCnpj,
  lancar,
  registrarTrace,
  semNbsp,
} from "./apoio";

test.describe.configure({ mode: "serial" });

const suf = Date.now().toString().slice(-6);
const A = { nome: `E2E Clínica Alfa ${suf}`, cnpj: cnpj(`71${suf}0001`) };
const B = { nome: `E2E Engenharia Beta ${suf}`, cnpj: cnpj(`72${suf}0001`) };
const C = { nome: `E2E Consultoria Gama ${suf}`, cnpj: cnpj(`73${suf}0001`) };
const ids: Record<string, string> = {};
let page: Page;

test.beforeAll(async ({ browser }) => {
  fs.rmSync(SAIDA, { recursive: true, force: true });
  page = await browser.newPage();
});

test.afterAll(async () => {
  await page.close();
});

async function cadastrarPelaTela(nome: string, cnpjEmpresa: string): Promise<string> {
  await page.goto("/empresas/nova");
  await page.getByLabel("Nome").fill(nome);
  await page.locator("input[name=cnpj]").fill(cnpjEmpresa);
  await page.locator("input[name=inicio_atividade]").fill("2020-01");
  await page.locator("select[name=pacote]").selectOption("monitoramento");
  await page.locator("input[name=honorario]").fill("500,00");
  await page.getByRole("button", { name: "Cadastrar" }).click();
  await page.waitForURL(/\/empresas\/[0-9a-f-]{36}$/);
  return page.url().split("/").pop()!;
}

async function abrirFatorR(companyId: string, pa: string): Promise<void> {
  await page.goto(`/empresas/${companyId}`);
  await page.locator("input[name=pa]").fill(pa);
  await page.getByTestId("painel-fator-r").waitFor();
}

test("§13.1a login do escritório", async () => {
  await entrar(page);
  await expect(page.getByRole("heading", { name: "Carteira" })).toBeVisible();
});

test("§13.1b duas empresas com 12 competências cada", async () => {
  ids.A = await cadastrarPelaTela(A.nome, A.cnpj);
  // Empresa A pela grade da ficha (12 competências). A grade abre nos 12 meses anteriores ao
  // mês corrente; se o E2E rodar em outro mês, navega até a janela do PA 09/2026.
  await page.goto(`/empresas/${ids.A}`);
  await page.locator("tr[data-competencia]").first().waitFor();
  for (let tentativas = 0; tentativas < 24; tentativas++) {
    const ultima = await page
      .locator("tr[data-competencia]")
      .last()
      .getAttribute("data-competencia");
    if (ultima === "2026-08") break;
    const botao = ultima! > "2026-08" ? "← 12 meses anteriores" : "12 meses seguintes →";
    await page.getByRole("button", { name: botao }).click();
    await page.locator("tr[data-competencia]").first().waitFor();
  }
  for (const mes of MESES) {
    const linha = page.locator(`tr[data-competencia='${mes}']`);
    await linha.getByLabel(`Receita bruta ${mes}`).fill("50.000,00");
    await linha.getByLabel(`Pró-labore ${mes}`).fill("10.000,00");
    await linha.getByLabel(`CPP recolhida ${mes}`).fill("2.000,00");
    await linha.getByRole("button", { name: "Salvar" }).click();
    await expect(page.locator(`[data-testid=folha-${mes}]`)).toHaveText(/12\.000,00/);
  }
  ids.B = await cadastrarPelaTela(B.nome, B.cnpj);
  await lancar(page.request, ids.B, {
    receita_bruta: "40000.00",
    pro_labore: "11000.00",
    salarios: "2000.00",
  });
  const contagem = async (id: string) =>
    (
      await (
        await page.request.get(`${API}/companies/${id}/movements?de=2025-09&ate=2026-08`)
      ).json()
    ).length;
  expect(await contagem(ids.A)).toBe(12);
  expect(await contagem(ids.B)).toBe(12);
});

test("§13.1c Fator R do PA coincide com a conta manual da janela", async () => {
  // A: FS12 = 12 x (10.000 + 2.000 CPP; política do seed: CPP integra) = 144.000; RBT12 = 600.000.
  await abrirFatorR(ids.A, "2026-09");
  await expect(page.getByTestId("fator-r")).toHaveText("24,00%");
  expect(semNbsp(await page.getByTestId("rbt12").textContent())).toBe("R$ 600.000,00");
  expect(semNbsp(await page.getByTestId("fs12").textContent())).toBe("R$ 144.000,00");
  await expect(page.getByTestId("anexo")).toHaveText("Anexo V");
  // B: FS12 = 12 x 13.000 = 156.000; RBT12 = 480.000 -> 32,50%, Anexo III.
  await abrirFatorR(ids.B, "2026-09");
  await expect(page.getByTestId("fator-r")).toHaveText("32,50%");
  await expect(page.getByTestId("anexo")).toHaveText("Anexo III");
});

test("§13.2 trocar o PA reconstrói a janela sem recálculo manual", async () => {
  await abrirFatorR(ids.A, "2026-09");
  await expect(page.getByTestId("janela")).toHaveText("Janela: set/2025 a ago/2026");
  await page.getByRole("button", { name: "PA seguinte →" }).click();
  await expect(page.getByTestId("janela")).toHaveText("Janela: out/2025 a set/2026");
  await expect(page.locator("[data-mes='2026-09']")).toHaveAttribute("data-situacao", "faltante");
  await expect(page.locator("[data-mes='2025-09']")).toHaveCount(0);
});

test("§13.3 extrato texto com CNPJ conhecido vincula sozinho e não sobrescreve folha", async () => {
  // Folha já lançada na competência do PA do extrato (09/2026).
  const r = await page.request.put(`${API}/companies/${ids.A}/movements/2026-09`, {
    data: {
      receita_bruta: "51000.00",
      pro_labore: "10000.00",
      cpp: "2000.00",
      observacao: "manual",
    },
  });
  expect(r.status()).toBe(200);
  const antes = await r.json();
  const arquivo = path.join(SAIDA, `extrato-a-${suf}.txt`);
  fs.mkdirSync(SAIDA, { recursive: true });
  fs.writeFileSync(arquivo, EXTRATO_PADRAO.replaceAll("11.222.333/0001-81", formatarCnpj(A.cnpj)));
  await page.goto("/inbox");
  await page.locator("input[name=arquivo]").setInputFiles(arquivo);
  const resultado = page.getByTestId("resultado-upload");
  await expect(resultado).toContainText("vinculado", { timeout: 30_000 });
  await expect(resultado).toContainText("já tinha lançamento");
  const depois = (
    await (
      await page.request.get(`${API}/companies/${ids.A}/movements?de=2026-09&ate=2026-09`)
    ).json()
  )[0];
  expect(depois).toEqual(antes);
  const doc = (await (await page.request.get(`${API}/inbox?status=linked`)).json()).items.find(
    (d: { campos: { cnpj: string } }) => d.campos.cnpj === A.cnpj,
  );
  registrarTrace("parser_linked", doc.trace_id);
});

test("§13.4 extrato sem CNPJ da carteira fica needs_review", async () => {
  const arquivo = path.join(SAIDA, `extrato-desconhecido-${suf}.txt`);
  fs.writeFileSync(
    arquivo,
    EXTRATO_PADRAO.replaceAll("11.222.333/0001-81", formatarCnpj(cnpj(`79${suf}0001`))),
  );
  await page.goto("/inbox");
  await page.locator("input[name=arquivo]").setInputFiles(arquivo);
  const resultado = page.getByTestId("resultado-upload");
  await expect(resultado).toContainText("revisão", { timeout: 30_000 });
  await expect(resultado).toContainText("cnpj_nao_encontrado");
});

test("§13.5 semáforo separa <28%, 28-30% e ≥30%", async () => {
  const r = await page.request.post(`${API}/companies`, {
    data: { nome: C.nome, cnpj: C.cnpj, sujeita_fator_r: true, honorario_mensal: "300.00" },
  });
  ids.C = (await r.json()).id;
  await lancar(page.request, ids.C, { receita_bruta: "50000.00", pro_labore: "14500.00" }); // 29%
  await page.goto("/carteira");
  await page.locator("input[name=pa]").fill("2026-09");
  const tabela = page.getByTestId("tabela-carteira");
  await expect(tabela.locator("tr", { hasText: A.nome })).toHaveAttribute(
    "data-semaforo",
    "vermelho",
  );
  await expect(tabela.locator("tr", { hasText: C.nome })).toHaveAttribute(
    "data-semaforo",
    "amarelo",
  );
  await expect(tabela.locator("tr", { hasText: B.nome })).toHaveAttribute("data-semaforo", "verde");
});

test("§13.6 simulador devolve um dos três vereditos e persiste no trace", async () => {
  await page.goto(`/empresas/${ids.A}`);
  await page.locator("input[name=sim-pa]").fill("2026-09");
  await page.getByRole("button", { name: "Simular" }).click();
  await expect(page.getByTestId("veredito")).toHaveText(/Corrigir|Não forçar|Já na meta/, {
    timeout: 30_000,
  });
  const href = await page.getByTestId("link-trace-simulacao").getAttribute("href");
  const traceId = href!.split("/").pop()!;
  registrarTrace("simulacao", traceId);
  const detalhe = await (await page.request.get(`${API}/traces/${traceId}`)).json();
  expect(detalhe.trace.agente).toBe("consultor");
  expect(detalhe.decisao.simulation_id).toBeTruthy();
});

test("§12 priorizador devolve a fila com trace_id", async () => {
  await page.goto("/agentes");
  await page.locator("input[name=pa-agentes]").fill("2026-09");
  const chat = page.getByTestId("chat-priorizador");
  await chat.locator("input[name=mensagem]").fill("O que priorizar esta semana?");
  await chat.getByRole("button", { name: "Enviar" }).click();
  await expect(chat.getByTestId("fila-priorizador")).toContainText(A.nome, { timeout: 30_000 });
  const href = await chat.getByTestId("ver-trace").getAttribute("href");
  registrarTrace("priorizador", href!.split("/").pop()!);
});

test("§13.7 toda decisão de agente tem trace consultável com spans", async () => {
  const traces = JSON.parse(fs.readFileSync(path.join(SAIDA, "traces.json"), "utf8"));
  for (const traceId of Object.values(traces) as string[]) {
    const r = await page.request.get(`${API}/traces/${traceId}`);
    expect(r.status()).toBe(200);
  }
  await page.goto(`/observabilidade/traces/${traces.priorizador}`);
  await expect(page.getByTestId("trace-id")).toHaveText(traces.priorizador);
  await expect(page.getByTestId("timeline-spans")).toBeVisible({ timeout: 60_000 });
  for (const span of ["plan", "tool", "decide", "render"]) {
    await expect(page.locator(`[data-span='${span}']`).first()).toBeVisible();
  }
});

test("§13.8 contador dá nota humana no trace", async () => {
  const traces = JSON.parse(fs.readFileSync(path.join(SAIDA, "traces.json"), "utf8"));
  await page.goto(`/observabilidade/traces/${traces.parser_linked}`);
  await page.locator("input[name=nota][value=erro]").check();
  await page.getByRole("button", { name: "Registrar nota" }).click();
  await expect(page.locator("p[role=alert]")).toContainText("obrigatório");
  await page
    .locator("textarea[name=comentario]")
    .fill("Conferência E2E: comentário obrigatório em erro.");
  await page.getByRole("button", { name: "Registrar nota" }).click();
  await expect(page.getByText("Nota registrada.")).toBeVisible();
  await expect(page.getByTestId("evals-humanas")).toContainText("Conferência E2E");
});

test("§13.9 UI afirma que o PGDAS-D é a apuração oficial em todas as telas", async () => {
  const rotas = [
    "/carteira",
    "/empresas",
    "/empresas/nova",
    `/empresas/${ids.A}`,
    `/empresas/${ids.A}/editar`,
    "/inbox",
    "/agentes",
    "/observabilidade",
  ];
  for (const rota of rotas) {
    await page.goto(rota);
    await expect(page.getByTestId("disclaimer-pgdas"), rota).toContainText(DISCLAIMER);
  }
  const anonimo = await page.context().browser()!.newPage();
  await anonimo.goto("/login");
  await expect(anonimo.getByTestId("disclaimer-pgdas")).toContainText(DISCLAIMER);
  await anonimo.close();
});

test("§13.10 não existe login nem cadastro de cliente", async () => {
  for (const rota of [
    "/cadastro",
    "/signup",
    "/registro",
    "/cliente",
    "/cliente/login",
    "/portal",
  ]) {
    const resposta = await page.goto(rota);
    expect(resposta?.status(), rota).toBe(404);
  }
  for (const rota of ["/auth/register", "/auth/signup", "/clientes/login"]) {
    const r = await page.request.post(`${API}${rota}`, { data: {} });
    expect([404, 405], rota).toContain(r.status());
  }
});
