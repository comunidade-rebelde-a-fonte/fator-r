# Fixtures do parser PGDAS-D

Cada pasta tem `documento.(pdf|txt)` e `expected.json` (campos esperados, faixa de confiança e,
se houver, o motivo esperado).

## Sintéticas (`"sintetica": true`)

Geradas por `scripts/gerar_fixtures_pgdas.py`. Imitam o layout do "Extrato do Simples Nacional"
e cobrem variações de rótulo, espaçamento, encoding, campos ausentes, CNPJ inválido e PDF sem
camada de texto. **Não substituem extratos reais.**

## Reais anonimizadas (P-03)

Só entram depois da revisão do usuário (CLAUDE.md §5.3). Nunca commitar extrato real sem
anonimização. Extratos brutos ficam fora do repositório (`fixtures/pgdas/real/` está no
`.gitignore`).

Como anonimizar:
1. Trocar CNPJ por um CNPJ válido fictício (manter os dígitos verificadores corretos).
2. Trocar nome empresarial, endereço e dados de sócios.
3. Manter os valores (RPA, RBT12, FS12, Fator r, DAS), que são o que o parser precisa ler, ou
   aplicar o mesmo fator multiplicativo em todos para preservar a consistência Fator r = FS12/RBT12.
4. Criar a pasta `real_<n>/` com `documento.pdf` e `expected.json` com `"sintetica": false`.
