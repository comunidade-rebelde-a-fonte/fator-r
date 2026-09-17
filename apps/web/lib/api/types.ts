import type { components } from "./schema";

type S = components["schemas"];

export type CompanyOut = S["CompanyOut"];
export type CompanyIn = S["CompanyIn"];
export type CompanyPatch = S["CompanyPatch"];
export type CompanyList = S["CompanyList"];
export type MovementIn = S["MovementIn"];
export type MovementOut = S["MovementOut"];
export type Pacote = NonNullable<CompanyOut["pacote"]>;
export type Origem = MovementOut["origem"];
export type FatorROut = S["FatorROut"];
export type Semaforo = NonNullable<FatorROut["semaforo"]>;
export type CarteiraOut = S["CarteiraOut"];
export type LinhaCarteiraOut = S["LinhaCarteiraOut"];
export type ResumoOut = S["ResumoOut"];
export type TraceList = S["TraceList"];
export type TraceResumoOut = S["TraceResumoOut"];
export type TraceDetalheOut = S["TraceDetalheOut"];
export type NotaHumanaIn = S["NotaHumanaIn"];
export type DocumentoOut = S["DocumentoOut"];
export type DocumentoList = S["DocumentoList"];
export type StatusDocumento = DocumentoOut["status"];
export type SimulacaoIn = S["SimulacaoIn"];
export type SimulacaoOut = S["SimulacaoOut"];
export type RespostaAgente = S["RespostaAgente"];
