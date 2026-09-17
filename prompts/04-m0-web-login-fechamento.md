# 04 — M0 · Login e layout no web + fechamento do M0 🏁 (T-012)

Branch sugerida: `feat/m0-fundacao`

## Contexto
- `docs/tasks.md` → T-012 e **Aceite M0**.
- `docs/prd.md` → §8 (conformidade: o PGDAS-D prevalece), §13.
- `CLAUDE.md` → §6.1 (item UI), §6.2 (marco pronto), §8 etapa 8, §10.2.

## Execute
1. **T-012:**
   - tela `/login`;
   - layout autenticado `(app)` com navegação Carteira · Empresas · Inbox · Agentes · Observabilidade (placeholders "em construção" nas páginas ainda não implementadas);
   - redireciona para `/login` sem sessão (usa `GET /auth/me`);
   - logout;
   - **componente único `Disclaimer`** fixo no rodapé: "Esta plataforma não é a apuração oficial. O PGDAS-D da Receita Federal prevalece.";
   - estados de carregando e de erro no login.
2. **Verifique no navegador:** login, navegação, logout e acesso direto a uma rota protegida sem sessão.
3. **Fechamento do M0 (etapa 8).** Verifique cada item do "Aceite M0" com evidência:
   - `make up` sobe api, web, db e Langfuse; `/health` devolve 200; a UI do Langfuse abre;
   - login e logout funcionam; rota protegida sem cookie devolve 401;
   - não existe rota nem tela de cadastro ou login de cliente (procure por `signup`, `register`, `cliente` em rotas);
   - CI verde (ou suíte local equivalente, se o repo não tiver remoto).

## Não pode
- Nenhuma tela de cadastro self-service ou "esqueci a senha" (fora do escopo v1).

## Gates
`make lint`, `make test`, `tsc --noEmit`, build do web e verificação manual no navegador.

## Pronto quando
- T-012 `[x]`.
- Relatório de fechamento com uma tabela "item do Aceite M0 → evidência".
- **Pergunta final:** "Confirma o fechamento do M0?" Não avance sem a minha resposta.
