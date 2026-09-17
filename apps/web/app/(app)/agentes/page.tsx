"use client";

import Link from "next/link";
import { useState } from "react";

import { Chat } from "@/components/agentes/Chat";
import { SemaforoBadge } from "@/components/fator-r/SemaforoBadge";
import { perguntarConsultor, perguntarPriorizador } from "@/lib/api/agents";
import type { RespostaAgente, Semaforo } from "@/lib/api/types";
import { competenciaAtual, formatarPercentual, formatarReais } from "@/lib/format";

type ItemFila = {
  posicao: number;
  company_id: string;
  empresa: string;
  semaforo: Semaforo;
  fator_r: string | null;
  economia_12m: string | null;
  acao: string;
};

function Fila({ resposta }: { resposta: RespostaAgente }) {
  const fila = (resposta.decisao.fila ?? []) as ItemFila[];
  if (fila.length === 0) return null;
  return (
    <table className="mt-2 w-full text-left text-xs" data-testid="fila-priorizador">
      <thead className="border-b text-zinc-500">
        <tr>
          <th className="py-1">#</th>
          <th>Empresa</th>
          <th>Semáforo</th>
          <th className="text-right">Fator R</th>
          <th className="text-right">Economia 12m</th>
          <th>Ação</th>
        </tr>
      </thead>
      <tbody>
        {fila.map((item) => (
          <tr key={item.company_id} className="border-b last:border-0">
            <td className="py-1">{item.posicao}</td>
            <td>
              <Link href={`/empresas/${item.company_id}`} className="underline">
                {item.empresa}
              </Link>
            </td>
            <td>
              <SemaforoBadge semaforo={item.semaforo} />
            </td>
            <td className="text-right">{formatarPercentual(item.fator_r)}</td>
            <td className="text-right">{formatarReais(item.economia_12m)}</td>
            <td>{item.acao}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function AgentesPage() {
  const [pa, setPa] = useState(competenciaAtual());
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Agentes</h1>
        <label className="flex items-center gap-2 text-sm">
          PA da carteira
          <input
            type="month"
            name="pa-agentes"
            value={pa}
            onChange={(e) => setPa(e.target.value)}
            className="rounded border border-zinc-300 px-2 py-1"
          />
        </label>
      </div>
      <p className="text-sm text-zinc-600">
        Os agentes só classificam o pedido e redigem a resposta. Todo cálculo vem do motor do
        sistema, e cada resposta tem trace.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <Chat
          titulo="Priorizador"
          placeholder="O que priorizar esta semana?"
          testid="chat-priorizador"
          enviar={(m) => perguntarPriorizador(m, pa)}
          renderDecisao={(r) => <Fila resposta={r} />}
        />
        <Chat
          titulo="Consultor"
          placeholder="Como está a empresa X? Simule a correção da empresa Y."
          testid="chat-consultor"
          enviar={(m) => perguntarConsultor(m)}
        />
      </div>
    </section>
  );
}
