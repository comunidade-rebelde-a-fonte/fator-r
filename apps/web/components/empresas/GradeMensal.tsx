"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { OrigemBadge } from "@/components/empresas/Badges";
import { Botao } from "@/components/ui/Botao";
import { classesCampo } from "@/components/ui/Campo";
import { Carregando, Erro } from "@/components/ui/Estado";
import { lancarMovimento, listarMovimentos } from "@/lib/api/companies";
import type { MovementOut } from "@/lib/api/types";
import {
  competenciaAtual,
  decimalParaEntradaBR,
  formatarReais,
  rotuloCompetencia,
  somarMeses,
  valorBRParaDecimal,
} from "@/lib/format";

const CAMPOS = [
  ["receita_bruta", "Receita bruta"],
  ["pro_labore", "Pró-labore"],
  ["salarios", "Salários + 13º/férias"],
  ["cpp", "CPP recolhida"],
  ["fgts", "FGTS recolhido"],
] as const;
type Campo = (typeof CAMPOS)[number][0];

function LinhaCompetencia({
  companyId,
  competencia,
  movimento,
}: {
  companyId: string;
  competencia: string;
  movimento?: MovementOut;
}) {
  const queryClient = useQueryClient();
  const inicial = Object.fromEntries(
    CAMPOS.map(([c]) => [c, decimalParaEntradaBR(movimento?.[c])]),
  ) as Record<Campo, string>;
  const [valores, setValores] = useState(inicial);
  const [observacao, setObservacao] = useState(movimento?.observacao ?? "");
  const [estado, setEstado] = useState<"ocioso" | "salvando" | "salvo" | "erro">("ocioso");
  const [mensagem, setMensagem] = useState("");
  // O PGDAS-D só informa a folha total do mês: sem pró-labore, CPP e FGTS separados.
  const [detalhando, setDetalhando] = useState(false);
  const folhaDoPgdas = movimento?.origem === "pgdas" && !detalhando;

  async function salvar() {
    const corpo = {} as Record<Campo, string>;
    for (const [campo, rotulo] of CAMPOS) {
      const decimal = valorBRParaDecimal(valores[campo]);
      if (decimal === null) {
        setEstado("erro");
        setMensagem(`${rotulo}: valor inválido`);
        return;
      }
      corpo[campo] = decimal;
    }
    setEstado("salvando");
    try {
      await lancarMovimento(companyId, competencia, { ...corpo, observacao: observacao || null });
      await queryClient.invalidateQueries({ queryKey: ["movimentos", companyId] });
      await queryClient.invalidateQueries({ queryKey: ["fator-r", companyId] });
      setEstado("salvo");
      setMensagem("");
    } catch {
      setEstado("erro");
      setMensagem("Não foi possível salvar");
    }
  }

  return (
    <tr className="border-b align-top last:border-0" data-competencia={competencia}>
      <td className="py-2 pr-2 font-medium whitespace-nowrap">{rotuloCompetencia(competencia)}</td>
      <td className="pr-2">
        {movimento ? (
          <OrigemBadge origem={movimento.origem} />
        ) : (
          <span className="text-muted text-xs">sem lançamento</span>
        )}
      </td>
      {CAMPOS.map(([campo, rotulo]) =>
        folhaDoPgdas && campo !== "receita_bruta" ? null : (
          <td key={campo} className="pr-2">
            <input
              aria-label={`${rotulo} ${competencia}`}
              inputMode="decimal"
              value={valores[campo]}
              onChange={(e) => {
                setValores({ ...valores, [campo]: e.target.value });
                setEstado("ocioso");
              }}
              className={`w-28 px-1.5 py-1 text-right ${classesCampo}`}
            />
          </td>
        ),
      )}
      {folhaDoPgdas && movimento && (
        <td colSpan={4} className="pr-2 text-sm" data-testid={`folha-pgdas-${competencia}`}>
          {Number(movimento.salarios) > 0 ? (
            <>
              Folha declarada no PGDAS-D: <strong>{formatarReais(movimento.salarios)}</strong>
              <span className="text-muted block text-xs">
                O extrato não separa pró-labore, salários, CPP e FGTS.
              </span>
            </>
          ) : (
            <span className="text-muted">Folha não informada no extrato</span>
          )}
          <button
            type="button"
            onClick={() => setDetalhando(true)}
            className="mt-1 block text-xs underline"
          >
            Detalhar folha
          </button>
        </td>
      )}
      <td className="pr-2 text-right whitespace-nowrap" data-testid={`folha-${competencia}`}>
        {movimento ? formatarReais(movimento.folha_mes) : "—"}
      </td>
      <td className="pr-2">
        <input
          aria-label={`Observação ${competencia}`}
          value={observacao}
          onChange={(e) => setObservacao(e.target.value)}
          className={`w-40 px-1.5 py-1 ${classesCampo}`}
        />
      </td>
      <td className="whitespace-nowrap">
        <Botao variante="fantasma" tamanho="sm" onClick={salvar} disabled={estado === "salvando"}>
          {estado === "salvando" ? "..." : "Salvar"}
        </Botao>
        {estado === "salvo" && <span className="text-ok ml-1 text-xs">salvo</span>}
        {estado === "erro" && (
          <span role="alert" className="text-danger-soft ml-1 text-xs">
            {mensagem}
          </span>
        )}
      </td>
    </tr>
  );
}

export function GradeMensal({ companyId, fim: fimInicial }: { companyId: string; fim?: string }) {
  const [fim, setFim] = useState(fimInicial ?? somarMeses(competenciaAtual(), -1));
  const inicio = somarMeses(fim, -11);
  const movimentos = useQuery({
    queryKey: ["movimentos", companyId, inicio, fim],
    queryFn: () => listarMovimentos(companyId, inicio, fim),
  });
  const competencias = Array.from({ length: 12 }, (_, i) => somarMeses(inicio, i));

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm">
        <Botao variante="fantasma" tamanho="sm" onClick={() => setFim(somarMeses(fim, -12))}>
          ← 12 meses anteriores
        </Botao>
        <span className="text-muted">
          {rotuloCompetencia(inicio)} a {rotuloCompetencia(fim)}
        </span>
        <Botao variante="fantasma" tamanho="sm" onClick={() => setFim(somarMeses(fim, 12))}>
          12 meses seguintes →
        </Botao>
      </div>
      {movimentos.isPending && <Carregando />}
      {movimentos.isError && (
        <Erro
          texto="Não foi possível carregar os movimentos."
          onRetry={() => movimentos.refetch()}
        />
      )}
      {movimentos.isSuccess && (
        <div className="overflow-x-auto">
          <table className="text-left text-sm [&_th]:pr-3 [&_th]:whitespace-nowrap">
            <thead className="text-muted border-b text-xs">
              <tr>
                <th className="py-2">Competência</th>
                <th>Origem</th>
                {CAMPOS.map(([c, r]) => (
                  <th key={c}>{r}</th>
                ))}
                <th className="text-right">Folha do mês</th>
                <th>Observação</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {competencias.map((c) => (
                <LinhaCompetencia
                  key={`${c}-${movimentos.dataUpdatedAt}`}
                  companyId={companyId}
                  competencia={c}
                  movimento={movimentos.data.find((m) => m.competencia === c)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
