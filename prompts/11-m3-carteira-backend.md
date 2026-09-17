# 11 — M3 · Carteira no backend e performance (T-301 a T-305)

Branch sugerida: `feat/m3-carteira`
Pré-condição: M2 fechado.

## Contexto
- `docs/tasks.md` → T-301 a T-305.
- `docs/prd.md` → §7.5 (carteira), §8 (performance), §9 (receita dos pacotes).
- `docs/plan.md` → §8 (consulta única).
- `CLAUDE.md` → §3.1, §3.3, §3.13, §7 (gate `perf`).

## Execute (ciclo §8 por tarefa)
1. **T-301 (`domain/carteira.py`, Python puro):**
   - recebe empresas + movimentos já carregados + tabelas + política + meta e reusa `fator_r.calcular` por empresa;
   - devolve linhas e KPIs: monitoradas, no V, no limite (28–30%), seguras, economia em jogo e soma dos honorários dos pacotes;
   - ordenação vermelho → amarelo → verde e, dentro do grupo, maior economia primeiro;
   - `dados_insuficientes` no fim.
2. **T-302:** ação sugerida por linha:
   - vermelho: "reunião de correção";
   - amarelo: "vigiar / simular";
   - verde: "manter";
   - dados insuficientes: "completar lançamentos".

   Os textos ficam em constante única.
3. **T-303:**
   - `GET /portfolio?pa=`, só empresas **ativas e sujeitas a Fator R**;
   - **uma** consulta para empresas e **uma** para todos os movimentos da janela (sem N+1: verificar com contagem de queries no teste).
4. **T-304:** `make seed-carga` gera 200 empresas × 24 meses num escritório de teste separado (nunca no escritório padrão).
5. **T-305:** teste `@pytest.mark.perf`: `/portfolio` com a carga do T-304 abaixo de 1 s (mediana de 5 execuções, banco aquecido).

## Testes obrigatórios
- Ordenação com empates.
- Empresa inativa ou não sujeita não aparece.
- KPIs somam certo.
- Contagem de queries ≤ 3.
- Isolamento (automático via T-110).

## Gates
`make lint`, `make test`, `pytest -m perf`, isolamento.

## Pronto quando
T-301 a T-305 `[x]` e o relatório com o tempo medido.
