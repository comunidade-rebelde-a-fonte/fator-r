# 00 — Kickoff e pré-requisitos

**Objetivo:** preparar a execução. Nenhum código de aplicação é escrito neste prompt.

## Leitura obrigatória
1. `CLAUDE.md` (contrato de execução), inteiro.
2. `docs/prd.md`, `docs/plan.md` e `docs/tasks.md`, inteiros.

## O que fazer
1. **Checagem de consistência.** Aponte qualquer conflito entre PRD, plano, tarefas e contrato: regra de domínio divergente, tarefa sem aceite, dependência circular, item "Fora" que aparece em tarefa. Não corrija nada sozinho; liste.
2. **P-01 — corrigir o PRD.** Esta é a única edição permitida neste prompt:
   - na PRD §7.6, trocar "no mês anterior ao PA" pela competência do próprio PA;
   - no PRD, adicionar uma nota curta apontando para as decisões da Plano §2.2;
   - subir a versão do PRD para 0.2 com a data de hoje;
   - marcar P-01 `[x]` em `docs/tasks.md`.
3. **Status dos demais pré-requisitos (P-02 a P-07).** Para cada um, diga:
   - o que exatamente preciso te entregar ou decidir;
   - qual prompt ele bloqueia (ver `prompts/README.md`);
   - o que dá para adiantar com dados sintéticos.
4. **Ambiente local.** Verifique, só leitura, se estão instalados e em que versão: `docker`, `docker compose`, `python3.12`, `uv`, `node`, `pnpm`/`npm`, `make`, `git`. Liste o que falta instalar.
5. **Git.** Informe a branch atual e se `main` existe. Não crie branch nem faça commit.

## Não pode
- Criar código, `apps/`, `infra/`, compose ou Makefile.
- Marcar qualquer outro `P-xx` como resolvido sem resposta minha.

## Relatório final
- Conflitos encontrados.
- P-01 feito (diff resumido).
- Tabela P-02..P-07: pendência · bloqueia · alternativa sintética.
- Ferramentas faltando.
- Próximo passo: `prompts/01-m0-monorepo-esqueleto.md`.
