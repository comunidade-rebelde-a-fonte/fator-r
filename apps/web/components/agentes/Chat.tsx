"use client";

import Link from "next/link";
import { useState, type FormEvent, type ReactNode } from "react";

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
    <div className="space-y-3 rounded border border-zinc-200 p-3 text-sm" data-testid={testid}>
      <h2 className="font-semibold">{titulo}</h2>
      <div className="max-h-[32rem] space-y-2 overflow-y-auto">
        {mensagens.map((m, i) => (
          <div
            key={i}
            data-autor={m.autor}
            className={`rounded p-2 ${m.autor === "analista" ? "bg-zinc-100" : "bg-sky-50"}`}
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
          <p role="status" className="text-zinc-500">
            Pensando...
          </p>
        )}
      </div>
      {erro && (
        <p role="alert" className="text-red-700">
          {erro}
        </p>
      )}
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          name="mensagem"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder={placeholder}
          className="flex-1 rounded border border-zinc-300 px-2 py-1.5"
        />
        <button
          type="submit"
          disabled={pensando}
          className="rounded bg-zinc-900 px-3 py-1.5 text-white disabled:opacity-60"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
