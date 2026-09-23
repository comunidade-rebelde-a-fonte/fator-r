"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Badge } from "@/components/ui/Badge";
import { Botao } from "@/components/ui/Botao";
import { classesCampo } from "@/components/ui/Campo";
import { Erro } from "@/components/ui/Estado";
import { Painel } from "@/components/ui/Painel";
import { historicoSimulacoes, simular } from "@/lib/api/simulations";
import type { SimulacaoOut } from "@/lib/api/types";
import {
  competenciaAtual,
  formatarPercentual,
  formatarReais,
  rotuloCompetencia,
} from "@/lib/format";

const VEREDITO = {
  ja_na_meta: { rotulo: "Já na meta", cor: "verde" },
  corrigir: { rotulo: "Corrigir", cor: "amarelo" },
  nao_forcar: { rotulo: "Não forçar", cor: "vermelho" },
} as const;

/** "11" (%) -> "0.11". Só converte a unidade digitada; nenhuma conta tributária. */
function percentualParaTaxa(valor: string): string | null {
  const numero = Number(valor.replace(",", "."));
  if (!Number.isFinite(numero) || numero < 0 || numero > 100) return null;
  return (numero / 100).toFixed(6);
}

function Linha({ rotulo, valor, testid }: { rotulo: string; valor: string; testid?: string }) {
  return (
    <div className="flex justify-between border-b py-1 last:border-0">
      <span className="text-muted">{rotulo}</span>
      <span className="font-medium" data-testid={testid}>
        {valor}
      </span>
    </div>
  );
}

function Resultado({ s }: { s: SimulacaoOut }) {
  const r = s.resultado as Record<string, string | null>;
  return (
    <Painel className="space-y-2 p-3 text-sm" data-testid="resultado-simulacao">
      <div className="flex items-center justify-between">
        {s.veredito ? (
          <span className="text-lg" data-testid="veredito">
            <Badge cor={VEREDITO[s.veredito].cor}>{VEREDITO[s.veredito].rotulo}</Badge>
          </span>
        ) : (
          <Badge>Dados insuficientes</Badge>
        )}
        <Link
          href={`/observabilidade/traces/${s.trace_id}`}
          className="text-xs underline"
          data-testid="link-trace-simulacao"
        >
          ver trace
        </Link>
      </div>
      <p>{s.texto}</p>
      <Linha rotulo="Fator R atual" valor={formatarPercentual(r.fator_atual)} />
      <Linha rotulo="Reforço de folha (12 meses)" valor={formatarReais(r.reforco_12m)} />
      <Linha rotulo="Reforço por mês" valor={formatarReais(r.reforco_mensal)} />
      <Linha rotulo="Pró-labore extra por mês" valor={formatarReais(r.pro_labore_extra_mensal)} />
      <Linha rotulo="Custo INSS do sócio" valor={formatarReais(r.custo_inss)} />
      <Linha rotulo="Custo IRRF" valor={formatarReais(r.custo_irrf)} />
      <Linha rotulo="Economia de DAS no horizonte" valor={formatarReais(r.economia_horizonte)} />
      <Linha rotulo="Líquido" valor={formatarReais(r.liquido)} testid="liquido" />
    </Painel>
  );
}

export function Simulador({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient();
  const [pa, setPa] = useState(competenciaAtual());
  const [meta, setMeta] = useState("");
  const [fracao, setFracao] = useState("100");
  const [inss, setInss] = useState("11");
  const [irrf, setIrrf] = useState("27,5");
  const [horizonte, setHorizonte] = useState("12");
  const [resultado, setResultado] = useState<SimulacaoOut | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [simulando, setSimulando] = useState(false);
  const historico = useQuery({
    queryKey: ["simulacoes", companyId],
    queryFn: () => historicoSimulacoes(companyId),
  });

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErro(null);
    const taxas = [fracao, inss, irrf].map(percentualParaTaxa);
    const metaTaxa = meta ? percentualParaTaxa(meta) : null;
    if (taxas.some((t) => t === null) || (meta && metaTaxa === null)) {
      setErro("Use percentuais entre 0 e 100.");
      return;
    }
    setSimulando(true);
    try {
      const s = await simular(companyId, {
        pa,
        meta: metaTaxa,
        fracao_pro_labore: taxas[0]!,
        inss: taxas[1]!,
        irrf: taxas[2]!,
        horizonte_meses: Number(horizonte),
      });
      setResultado(s);
      await queryClient.invalidateQueries({ queryKey: ["simulacoes", companyId] });
    } catch {
      setErro("Não foi possível simular. Confira os parâmetros (meta mínima de 28%).");
    } finally {
      setSimulando(false);
    }
  }

  const campo = `mt-1 block w-full px-2 py-1 ${classesCampo}`;
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <form onSubmit={onSubmit} className="grid grid-cols-2 gap-3 text-sm">
        <label>
          PA
          <input
            type="month"
            name="sim-pa"
            value={pa}
            onChange={(e) => setPa(e.target.value)}
            className={campo}
          />
        </label>
        <label>
          Meta (%) <span className="text-muted text-xs">vazio = do escritório</span>
          <input
            name="sim-meta"
            value={meta}
            onChange={(e) => setMeta(e.target.value)}
            placeholder="30"
            className={campo}
          />
        </label>
        <label>
          Fração do reforço em pró-labore (%)
          <input
            name="sim-fracao"
            value={fracao}
            onChange={(e) => setFracao(e.target.value)}
            className={campo}
          />
        </label>
        <label>
          Horizonte no Anexo III (meses)
          <input
            type="number"
            min={1}
            max={60}
            name="sim-horizonte"
            value={horizonte}
            onChange={(e) => setHorizonte(e.target.value)}
            className={campo}
          />
        </label>
        <label>
          INSS do sócio (%)
          <input
            name="sim-inss"
            value={inss}
            onChange={(e) => setInss(e.target.value)}
            className={campo}
          />
        </label>
        <label>
          IRRF marginal (%)
          <input
            name="sim-irrf"
            value={irrf}
            onChange={(e) => setIrrf(e.target.value)}
            className={campo}
          />
        </label>
        <p className="text-accent-soft col-span-2 text-xs" data-testid="aviso-inss">
          INSS sem teto na v1: o custo pode ficar superestimado para pró-labore alto.
        </p>
        {erro && (
          <p role="alert" className="text-danger-soft col-span-2">
            {erro}
          </p>
        )}
        <div className="col-span-2">
          <Botao type="submit" disabled={simulando}>
            {simulando ? "Simulando..." : "Simular"}
          </Botao>
        </div>
      </form>

      <div className="space-y-3">
        {resultado && <Resultado s={resultado} />}
        <div className="text-sm">
          <h3 className="font-display tracking-wide uppercase">Últimas simulações</h3>
          {historico.isError && <Erro texto="Não foi possível carregar o histórico." />}
          {historico.data?.length === 0 && <p className="text-muted">Nenhuma simulação ainda.</p>}
          <ul className="space-y-1" data-testid="historico-simulacoes">
            {historico.data?.map((s) => (
              <li key={s.simulation_id} className="flex items-center gap-2">
                {s.veredito ? (
                  <Badge cor={VEREDITO[s.veredito].cor}>{VEREDITO[s.veredito].rotulo}</Badge>
                ) : (
                  <Badge>insuficiente</Badge>
                )}
                <span>PA {rotuloCompetencia(s.pa)}</span>
                <span className="text-muted">
                  líquido {formatarReais((s.resultado as Record<string, string | null>).liquido)}
                </span>
                <Link href={`/observabilidade/traces/${s.trace_id}`} className="text-xs underline">
                  trace
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
