# Prompts de execução — Fator R v1

Sequência de prompts para executar `docs/tasks.md` seguindo o contrato do `CLAUDE.md`.

## Como usar

1. Rode **um prompt por sessão**, na ordem numérica. Abra uma sessão nova (ou use `/clear`) antes de cada um.
2. Cole o conteúdo do arquivo como mensagem. O `CLAUDE.md` já é carregado automaticamente.
3. Só avance para o próximo prompt quando o anterior terminar com o relatório da etapa 7 (CLAUDE.md §8) e todas as tarefas dele estiverem `[x]` em `docs/tasks.md`.
4. Prompts que fecham marco (marcados com 🏁) terminam pedindo sua confirmação. Confirme antes de seguir.
5. Commit, branch e PR só acontecem se você pedir (CLAUDE.md §5.5). Cada prompt indica o nome da branch sugerida.

## Se um prompt parar

O agente deve parar quando houver bloqueio (CLAUDE.md §9): pré-requisito `P-xx` pendente, conflito entre documentos, gate falhando por causa externa. Resolva o bloqueio e **rode o mesmo prompt de novo**: ele retoma pelas tarefas ainda `[ ]`.

## Sequência

| # | Arquivo | Marco | Tarefas | Pré-requisitos |
|---|---|---|---|---|
| 00 | `00-kickoff-pre-requisitos.md` | — | P-01..P-07 (checagem), leitura | — |
| 01 | `01-m0-monorepo-esqueleto.md` | M0 | T-001..T-004 | — |
| 02 | `02-m0-langfuse-make-ci.md` | M0 | T-005..T-007 | P-06 (recomendado) |
| 03 | `03-m0-auth-backend-seed.md` | M0 | T-008..T-011 | P-02 (valor do seed) |
| 04 | `04-m0-web-login-fechamento.md` 🏁 | M0 | T-012 + aceite M0 | — |
| 05 | `05-m1-schema-rls-repositorios.md` | M1 | T-101..T-105 | — |
| 06 | `06-m1-api-empresas-movimentos.md` | M1 | T-106, T-107, T-110 | — |
| 07 | `07-m1-web-cadastro-fechamento.md` 🏁 | M1 | T-108, T-109 + aceite M1 | — |
| 08 | `08-m2-tabelas-janela.md` | M2 | T-201, T-202 | P-04 |
| 09 | `09-m2-motor-fator-r.md` | M2 | T-203..T-205 | P-05, P-07 |
| 10 | `10-m2-endpoint-ficha-fechamento.md` 🏁 | M2 | T-206, T-207 + aceite M2 | — |
| 11 | `11-m3-carteira-backend.md` | M3 | T-301..T-305 | — |
| 12 | `12-m3-web-carteira-fechamento.md` 🏁 | M3 | T-306 + aceite M3 | — |
| 13 | `13-m4-tracer-guarda.md` | M4 | T-401..T-404 | — |
| 14 | `14-m4-instrumentacao-scores-echo.md` | M4 | T-405..T-408, T-411 | — |
| 15 | `15-m4-api-web-observabilidade-fechamento.md` 🏁 | M4 | T-409, T-410 + aceite M4 | — |
| 16 | `16-m5-upload-inbox.md` | M5 | T-501..T-503 | — |
| 17 | `17-m5-parser-pgdas.md` | M5 | T-504..T-508 | P-03 |
| 18 | `18-m5-agente-parser-ouro.md` | M5 | T-509..T-512 | — |
| 19 | `19-m5-dataset-web-inbox-fechamento.md` 🏁 | M5 | T-513, T-514 + aceite M5 | — |
| 20 | `20-m6-simulador.md` | M6 | T-601..T-604 | — |
| 21 | `21-m6-llm-plan-render-guardas.md` | M6 | T-605..T-608 | — |
| 22 | `22-m6-agentes-rotina-web-fechamento.md` 🏁 | M6 | T-609..T-613 + aceite M6 | — |
| 23 | `23-m7-backup-seguranca-disclaimer.md` | M7 | T-701..T-704 | — |
| 24 | `24-m7-e2e-aceite-v1.md` 🏁 | M7 | T-705..T-708 + aceite v1 | P-01..P-07 todos |

Paralelismo possível (tasks.md): depois do prompt 10, a trilha M3 (11–12) e a trilha M4 (13–15) podem rodar em sessões separadas, em worktrees diferentes.
