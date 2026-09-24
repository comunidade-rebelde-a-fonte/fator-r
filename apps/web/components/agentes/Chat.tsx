"use client";

import Link from "next/link";
import { useState, type FormEvent, type ReactNode } from "react";

import { Botao } from "@/components/ui/Botao";
import { classesCampo } from "@/components/ui/Campo";
import { Painel } from "@/components/ui/Painel";
import type { RespostaAgente } from "@/lib/api/types";

type Mensagem = { autor: "analista" | "agente"; texto: string; resposta?: RespostaAgente };

export function Chat({
  titulo,
  placeholder,
  enviar,
  renderDecisao,
  testid,
}: {
  titulo: string;
  placeholder: string;
  enviar: (mensagem: string) => Promise<RespostaAgente>;
  renderDecisao?: (resposta: RespostaAgente) => ReactNode;
  testid: string;
}) {
  const [texto, setTexto] = useState("");
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [pensando, setPensando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const pergunta = texto.trim();
    if (!pergunta) return;
    setErro(null);
    setTexto("");
    setMensagens((m) => [...m, { autor: "analista", texto: pergunta }]);
    setPensando(true);
    try {
      const resposta = await enviar(pergunta);
      setMensagens((m) => [...m, { autor: "agente", texto: resposta.texto, resposta }]);
    } catch {
      setErro("O agente não conseguiu responder agora.");
    } finally {
      setPensando(false);
    }
  }

  return (
    <Painel className="space-y-3 p-3 text-sm" data-testid={testid}>
      <h2 className="font-display text-lg tracking-wide uppercase">{titulo}</h2>
      <div className="max-h-[32rem] space-y-2 overflow-y-auto">
        {mensagens.map((m, i) => (
          <div
            key={i}
            data-autor={m.autor}
            className={`rounded-[4px] border p-2 ${
              m.autor === "analista" ? "border-accent/25 bg-accent/8" : "border-line bg-panel-2"
            }`}
          >
            <p className="whitespace-pre-line">{m.texto}</p>
            {m.resposta && (
              <>
                {renderDecisao?.(m.resposta)}
                <Link
                  href={`/observabilidade/traces/${m.resposta.trace_id}`}
                  className="mt-1 inline-block text-xs underline"
                  data-testid="ver-trace"
                >
                  ver trace
                </Link>
              </>
            )}
          </div>
        ))}
        {pensando && (
          <p role="status" className="text-muted">
            Pensando...
          </p>
        )}
      </div>
      {erro && (
        <p role="alert" className="text-danger-soft">
          {erro}
        </p>
      )}
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          name="mensagem"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder={placeholder}
          className={`flex-1 px-2 py-1.5 ${classesCampo}`}
        />
        <Botao type="submit" disabled={pensando}>
          Enviar
        </Botao>
      </form>
    </Painel>
  );
}
