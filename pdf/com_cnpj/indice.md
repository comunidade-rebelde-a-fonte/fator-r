# Exemplos de PGDAS-D com CNPJ fictício

Gerado por `apps/api/scripts/preencher_cnpj_ficticio.py` a partir dos PDFs de `pdf/`.
Os valores (RPA, RBT12, FS12, Fator r, DAS) são os mesmos do original; só a identificação
mascarada foi preenchida. Documentos fictícios, sem validade fiscal.

| Arquivo | CNPJ | Abertura | Município/UF |
|---|---|---|---|
| `01_servico_fator_r_abaixo_28.pdf` | 12.345.678/0001-95 | 12/03/2019 | SAO PAULO / SP |
| `02_comercio_sem_fator_r.pdf` | 23.456.789/0001-95 | 05/07/2017 | CAMPINAS / SP |
| `03_servico_sem_fator_r.pdf` | 34.567.890/0001-30 | 22/01/2021 | BELO HORIZONTE / MG |
| `04_servico_fator_r_acima_28.pdf` | 45.678.901/0001-75 | 30/09/2016 | CURITIBA / PR |
