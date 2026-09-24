PRD — Plataforma Fator R

Produto: monitoramento de Fator R e apoio à consultoria tributária para escritórios de contabilidade
Documento: Product Requirements Document
Status: rascunho para alinhamento
Versão: 0.3
Data: 2026-09-22
Acesso na v1: somente o contador (usuário do escritório)

Nota da v0.2: corrigida a §7.6 (RPA grava na competência do próprio PA).

Nota da v0.3: §7.6 ganha o cadastro de empresa a partir do extrato (M8), com confirmação do contador, a leitura do PA no formato de intervalo e o lançamento dos 12 meses anteriores (receita e folha declaradas) quando o extrato traz as tabelas mensais. Demais decisões de implementação que complementam este PRD estão em docs/plan.md §2.2 e no Registro de decisões (docs/plan.md §13).

1. Resumo

Escritórios de contabilidade precisam acompanhar o Fator R de vários clientes no Simples Nacional. O índice compara a folha de salários dos 12 meses anteriores ao período de apuração (FS12) com a receita bruta do mesmo período (RBT12). Se o resultado for ≥ 28%, receitas de serviço sujeitas à regra tributam no Anexo III; se for < 28%, tributam no Anexo V.

A avaliação é mensal e a janela é móvel. Um mês isolado de pró-labore alto não “liga” o benefício. Queda de folha ou alta de faturamento derruba o cliente para o anexo mais caro sem o escritório perceber a tempo.

Este produto é uma plataforma multi-empresa, com banco mês a mês, inbox de PGDAS-D, agentes que leem documento e propõem decisão, e uma camada de observabilidade para medir se esses agentes acertam.

O escritório não vende “sistema”. Vende continuidade no Anexo III e previsibilidade do DAS.

2. Problema

O cálculo é simples; o controle em dezenas de CNPJs não é.

Folha e receita mudam todo mês; o enquadramento pode inverter na competência seguinte.

O extrato do PGDAS-D confirma RBT12, FS12 e Fator R, mas não substitui a série mensal nem o split da folha (pró-labore vs CLT vs encargos).

Subir pró-labore para forçar 28% tem custo (INSS do sócio, IRRF). Sem simulador, a “correção” pode destruir a economia do DAS.

Sem trilha de qualidade, um agente que lê PDF vira caixa-preta — inaceitável em matéria tributária.

2.1 Não-problemas (fora deste PRD)

Substituir o PGDAS-D da Receita Federal.

Apurar e transmitir o DAS.

Folha de pagamento completa (eSocial como sistema de DP).

Planejamento tributário de Lucro Presumido / Real.

Portal do cliente na v1.

3. Objetivos

Objetivo

Como sabemos que funcionou

O escritório vê, toda competência, quem está no V, no limite e no III

Carteira com semáforo e janela de 12 meses preenchida

O contador recebe o extrato PGDAS e não redigita o que o documento já traz

Inbox com extração + vínculo por CNPJ + revisão quando a confiança for baixa

A recomendação de correção é defensável

Simulador DAS vs INSS+IRRF; veredito explícito

Dá para vender o serviço com número

Economia III vs V e fila de ação por cliente

Os agentes são auditáveis

Trace, spans, nota ouro e nota humana por corrida

3.1 Não-objetivos da v1

Login de cliente final.

White-label.

Integração nativa eSocial / NFS-e / certificado digital na Receita.

LLM tomando o cálculo do Fator R.

App mobile.

4. Usuários

4.1 Primário — contador / analista do escritório

Usa a plataforma no fechamento da competência: lança ou confere movimento, sobe PGDAS, lê a carteira, dispara reunião de correção.

4.2 Secundário — sócio do escritório

Olha semáforo, economia em jogo e receita do pacote Fator R. Não opera documento.

4.3 Fora da v1 — sócio da empresa cliente

Recebe relatório/WhatsApp gerado pelo escritório. Não acessa o sistema até a fase “externo”.

5. Contexto legal (requisito de domínio)

Base: LC 123/2006 art. 18 §§ 5º-J, 5º-K, 5º-M, 24 e 25; Resolução CGSN 140/2018 art. 26.

Fator r = FS12 ÷ RBT12

RBT12: receita bruta total (mercado interno + exportação) nos 12 meses anteriores ao PA.

FS12: remunerações a pessoas físicas (salários + pró-labore + 13º na competência da contribuição) + contribuição patronal previdenciária efetivamente recolhida + FGTS efetivamente recolhido, no mesmo período.

≥ 0,28 → Anexo III; < 0,28 → Anexo V.

Empresas com menos de 12 meses: proporcional conforme regra do PGDAS-D.

Não entra no numerador: distribuição de lucros, pró-labore sem INSS, PAT/alimentação não salarial, vale-transporte, reembolso, NF de PJ, verbas indenizatórias fora da base previdenciária.

Política do produto (decisão de escritório, documentada): haver divergência se a CPP embutida no DAS integra a FS12. A Resolução fala em valor efetivamente recolhido. A plataforma aplica uma política só por escritório, visível na ficha e no cálculo. Não deixa cada analista decidir por cliente.

Meta operacional interna (não legal): 30%.

Verde: ≥ 30%

Amarelo: 28% a 30%

Vermelho: < 28%

O corte legal continua 28%. O amarelo existe para o produto de “vigiar”.

6. Visão do produto

Escritório (v1)
├─ Carteira (semáforo, gap, economia DAS)
├─ Empresas (cadastro multi-CNPJ)
├─ Movimentos (série mensal)
├─ Inbox PGDAS-D
├─ Agentes (parser, consultor, priorizador)
└─ Observabilidade (traces, notas, KPIs)

Cliente (roadmap)
└─ Portal leitura + simulador autorizado

Um escritório. N empresas. Um banco. Dois perfis de permissão no futuro; um só agora.

7. Escopo funcional — v1

7.1 Autenticação e isolamento

Login do usuário do escritório.

Sessão autenticada.

Todas as consultas filtradas por firm_id.

Sem cadastro self-service de cliente.

Sem URL pública da ficha do contribuinte.

7.2 Cadastro de empresas

Campos mínimos: nome, CNPJ (único no escritório), CNAE, atividade, flag “sujeita a Fator R”, quantidade de sócios, contato, pacote comercial (monitoramento / correção / retainer), honorário mensal do pacote, ativo/inativo, notas.

Empresa fora do recorte Fator R pode existir no cadastro, mas não entra na carteira nem na fila do priorizador.

7.3 Movimentos mensais

Uma linha por empresa + competência (YYYY-MM):

receita bruta

pró-labore

salários + 13º/férias remuneradas

CPP patronal recolhida

FGTS recolhido

folha do mês = soma dos quatro itens de pessoal

origem: manual \| pgdas \| folha (futuro) \| agente

observação

Regras:

Upsert por (empresa, competência).

Origem pgdas pode gravar receita do mês a partir do RPA; não inventa split de folha.

Competência do movimento é o mês da receita/folha, não o PA. PA 09/2026 usa movimentos 2025-09 a 2026-08.

7.4 Motor Fator R

Entrada: empresa + PA.
Saída obrigatória:

janela (início/fim)

meses preenchidos / faltantes

RBT12, FS12, Fator R

anexo (III ou V)

folha mínima 28% e 30%

gap 12 meses e reforço mensal equivalente

alíquota efetiva Anexo III e Anexo V (tabelas vigentes)

economia estimada de DAS em 12 meses se III vs V

Se RBT12 = 0, anexo e alíquotas não são inventados; status = dados insuficientes.

7.5 Carteira

Lista só empresas ativas e sujeitas ao Fator R, para um PA selecionável (padrão: competência corrente).

Colunas mínimas: ação sugerida, nome, Fator R, anexo, RBT12, FS12, reforço mensal, economia 12 meses.

Ordenação padrão: vermelho → amarelo → verde; dentro do grupo, maior economia primeiro.

KPIs: quantidade monitorada, no V, no limite, seguras, soma da economia em jogo, soma dos honorários do pacote.

7.6 Inbox PGDAS-D

O PGDAS-D oficial não oferece XML estável ao escritório. O artefato de entrada da v1 é o extrato da apuração (PDF ou texto).

Fluxo:

Contador envia o arquivo.

Parser extrai, com confiança por documento: CNPJ, PA, RBT12, RPA, FS12, Fator R, valor do DAS, anexo se citado. O PA pode vir como mês/ano (09/2026) ou como intervalo dentro de um único mês (01/08/2026 a 31/08/2026); intervalo que atravessa meses não vira PA.

Para cadastro, o parser também lê o nome empresarial e sugere se a atividade é sujeita ao Fator R (fator r numérico → sim; "não se aplica" → não; sem indício → sem sugestão). Esses dados não entram na confiança nem na nota ouro.

Tentativa de vínculo pelo CNPJ da carteira.

Persistência do arquivo original + texto extraído + JSON dos campos + status.

Status: received \| parsed \| needs_review \| linked \| rejected.

Confiança < limiar (sugerido 0,40) ou CNPJ não encontrado → needs_review. Nenhuma escrita automática de folha.

Se vinculado e houver RPA, pode criar movimento de receita na competência do próprio PA (o RPA é a receita do período de apuração; ex.: PA 09/2026 → competência 2026-09) somente se a competência ainda não existir.

Se o extrato trouxer as tabelas de receitas e de folha de salários dos 12 meses anteriores ao PA, esses meses também são lançados (origem pgdas), desde que a soma das receitas bata com o RBT12 declarado e a soma da folha bata com a FS12 declarada. A folha entra como o total declarado no PGDAS-D, sem divisão entre pró-labore, salários, CPP e FGTS, e por isso a política de CPP do escritório não altera esses meses. Atividade sem fator r entra com folha zero. Nada é lançado em competência que já tenha lançamento. A data de abertura do CNPJ pré-preenche o início de atividade no cadastro pelo extrato.

CNPJ válido que não está na carteira: o documento continua em needs_review, e o contador pode cadastrar a empresa a partir do extrato, com o formulário pré-preenchido (CNPJ travado, nome e enquadramento editáveis). A empresa, o vínculo e a receita do PA só são gravados quando o contador confirma; nada é criado automaticamente. Se o CNPJ tiver sido cadastrado por outra pessoa nesse meio-tempo, o sistema oferece vincular à empresa existente.

O parser é heurístico. Erro de extração é esperado; por isso a observabilidade é requisito, não extra.

7.7 Simulador de correção

Para uma empresa e uma meta (padrão 30%):

reforço de folha em 12 meses e por mês

fração do reforço que seria pró-labore

INSS do sócio (padrão 11%, editável; respeito futuro ao teto)

IRRF marginal estimado (editável)

horizonte em meses no Anexo III

economia de DAS no horizonte

custo INSS+IRRF

líquido

veredito: já_na_meta \| corrigir \| nao_forcar

Regra de produto: se a economia anual de DAS for irrelevante para o porte (piso configurável no escritório; referência R$ 6.000), o veredito padrão é não forçar, mesmo com líquido positivo pequeno.

7.8 Agentes

Três agentes na v1. Linguagem natural no escritório; ferramentas no banco. Cálculo não passa por modelo generativo.

Agente

Gatilho

Ferramentas

Decisão

parser_pgdas

upload

parse, match CNPJ

campos + confiança + vínculo

consultor

chat / ficha

empresa, simulador

anexo, gap, veredito

priorizador

chat / rotina semanal

carteira

fila vermelha e amarela

Contrato de saída do agente: texto para o contador + decisão estruturada + trace_id.

Ponto de extensão futuro: apenas o roteamento de intenção (plan). Parse e aritmética permanecem determinísticos.

7.9 Observabilidade

Requisito de produto, não de engenharia escondida.

Toda corrida gera:

Trace: agente, gatilho, usuário, empresa, entrada, saída, status (ok / error / needs_review), confiança, latência, decisão

Spans: plan → parse ou tool → decide → render

Eval ouro: parser vs série mensal já lançada, campo a campo (CNPJ, PA, RBT12, FS12, Fator R, anexo), com tolerância percentual configurável

Eval humana: acerto / parcial / erro + comentário obrigatório no caso de erro

Painel:

corridas 24h e totais

pendências sem nota humana

acerto automático e acerto humano

por agente: volume, latência média, confiança média, erros, reviews

lista de traces filtrável por agente

Aceite mínimo de qualidade (meta de produto, revisar após 90 dias de uso real):

parser: ≥ 80% de acerto ouro em documentos vinculados do tipo “extrato texto”

fila de review humano zerada semanalmente pelo escritório

nenhuma recomendação corrigir sem simulador persistido no trace

8. Requisitos não funcionais

Tema

Requisito

Isolamento

Dado de um escritório não vaza para outro

Auditabilidade

Documento original do PGDAS retido; trace retido

Retenção v1

Mínimo 24 meses de movimentos e traces

Performance percebida

Carteira de até 200 empresas no PA corrente em tempo de tela única

Disponibilidade v1

Uso interno; backup diário do banco basta

Segurança

Sessão autenticada; upload restrito a PDF/TXT; arquivo fora da web root

Conformidade

Plataforma não é a apuração oficial; UI deve dizer que o PGDAS-D prevalece

Observabilidade

Sem trace, a corrida do agente não pode gravar decisão no banco

9. Oferta comercial (requisito de produto)

Três SKUs, desacoplados do honorário de escrituração:

Monitoramento — painel mensal + alerta se Fator R < 30% + parágrafo de leitura.

Correção — diagnóstico, simulador, ata de pró-labore/folha, 90 dias de acompanhamento.

Retainer — monitoramento + reunião trimestral + simulação de crescimento de receita.

Âncora de preço: fração da economia anual estimada de DAS (referência 8–15%), com piso de tempo do analista.

A carteira deve exibir a receita recorrente do pacote. Isso é feature, não relatório paralelo.

10. Fora de escopo (explícito)

Transmissão PGDAS-D / emissão de DAS / débito automático.

Cálculo de INSS com teto e múltiplos sócios na v1 (campo manual no simulador).

Importação OFX/ERP genérica.

Jurídico de planejamento agressivo ou folha fictícia. O produto recusa pró-labore sem INSS como FS12.

App do cliente, WhatsApp em massa e marca branca — fase externo.

11. Fases

Fase 0 — este PRD

Domínio, regras, o que o agente pode e não pode gravar.

Fase 1 — v1 escritório

Cadastro, movimentos, motor, carteira, inbox PGDAS, três agentes, observabilidade, pacotes comerciais.

Fase 2 — operação

Parser no layout do extrato RFB, lote de documentos, papéis (analista vs sócio), política de CPP configurável na UI, alerta no fechamento da folha, teto de INSS no simulador.

Fase 3 — externo

Portal do cliente (leitura + simulador autorizado), white-label, canal WhatsApp do agente no idioma do cliente, eSocial / NFS-e.

Critério para abrir a Fase 3: acerto humano do parser em produção ≥ meta da seção 7.9 e processo de review semanal no ar.

12. Histórias principais (v1)

Como analista, quero cadastrar o CNPJ e marcar se a atividade está sujeita a Fator R, para a carteira não misturar comércio com serviço intelectual.

Como analista, quero lançar receita e folha da competência, para o motor recalcular a janela de 12 meses.

Como analista, quero enviar o extrato PGDAS-D e ver CNPJ, PA, RBT12, FS12 e Fator R extraídos, para não redigitar o documento.

Como analista, quero que extração fraca caia em revisão e não grave folha, para não corromper a série.

Como sócio do escritório, quero a fila da semana (V e 28–30%) ordenada por economia de DAS, para priorizar reunião.

Como analista, quero simular o pró-labore extra e ver o líquido depois de INSS e IRRF, para não recomendar correção ruinosa.

Como analista, quero perguntar em linguagem natural “o que priorizar” e receber a fila com trace_id.

Como sócio do escritório, quero ver acerto, latência e pendências dos agentes, para não operar caixa-preta.

Como analista, quero marcar acerto/erro no trace do parser, para o painel de qualidade ter nota humana.

13. Regras de aceite (v1)

A v1 está aceita quando:

Um escritório opera ≥ 2 empresas com 12 competências cada e o Fator R do PA coincide com a conta manual da janela.

Trocar o PA reconstrói a janela (mês que entra / mês que sai) sem recálculo manual.

Upload de um extrato texto com CNPJ conhecido vincula sozinho e não sobrescreve folha já lançada.

Extrato sem CNPJ da carteira fica needs_review.

Semáforo da carteira separa \<28%, 28–30% e ≥30%.

Simulador devolve um dos três vereditos e persiste no trace.

Toda decisão de agente tem trace consultável, com spans.

Contador consegue dar nota humana no trace.

UI afirma que o PGDAS-D é a apuração oficial.

Não existe login de cliente.

14. Riscos

Risco

Mitigação

Parser quebra no PDF real da RFB

Inbox + review; ouro campo a campo; não gravar FS12 fatiada a partir do extrato

CPP no DAS interpretada de dois jeitos

Política única do escritório, visível no cálculo

Recomendação de pró-labore sem lastro

Veredito nao_forcar; recusa de folha sem INSS

Contador trata o agente como oficial

Disclaimer permanente; PGDAS prevalece

Abrir portal cedo e matar o honorário

Fase 3 condicionada a qualidade e processo

15. Métricas de produto (depois que existir uso real)

% da carteira sujeita a Fator R com 12/12 meses lançados no PA corrente

tempo médio entre fechamento de folha e alerta vermelho visto

% de recomendações corrigir aceitas em reunião

acerto ouro e acerto humano do parser_pgdas

receita recorrente dos pacotes Fator R / honorário total do escritório

16. Decisões em aberto

Limiar exato de confiança do parser (referência 0,40).

Piso de economia anual para recusar correção (referência R$ 6.000).

Se a CPP do DAS entra no numerador — decidir na política do escritório piloto.

Retenção de PDF além de 24 meses (LGPD / obrigação acessória).

Nome comercial do produto (interno: Fator R).

17. Entregável deste documento

Este PRD define o que construir e o que não construir.
Não inclui stack, telas finais nem cronograma de desenvolvimento.

Próximos documentos de planejamento, se necessário:

mapa de telas (wireframe textual)

contrato de eventos de observabilidade (nomes de trace, spans, rubrica)

política escrita de composição da FS12 para o escritório piloto