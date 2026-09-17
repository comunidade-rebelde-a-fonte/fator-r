"use client";

import { useState, type FormEvent } from "react";

import { ApiError } from "@/lib/api";
import type { CompanyIn, CompanyOut, Pacote } from "@/lib/api/types";
import { cnpjValido, mascararCnpj } from "@/lib/cnpj";
import { decimalParaEntradaBR, valorBRParaDecimal } from "@/lib/format";

type Props = {
  inicial?: CompanyOut;
  rotuloSalvar: string;
  onSalvar: (dados: CompanyIn) => Promise<void>;
};

function mensagemErro(error: unknown): string {
  if (error instanceof ApiError && error.status === 409)
    return "Já existe uma empresa com esse CNPJ neste escritório.";
  if (error instanceof ApiError && error.status === 422)
    return "Confira os campos: há algum valor inválido.";
  return "Não foi possível salvar. Tente novamente.";
}

export function EmpresaForm({ inicial, rotuloSalvar, onSalvar }: Props) {
  const [nome, setNome] = useState(inicial?.nome ?? "");
  const [cnpj, setCnpj] = useState(inicial?.cnpj_formatado ?? "");
  const [cnae, setCnae] = useState(inicial?.cnae ?? "");
  const [atividade, setAtividade] = useState(inicial?.atividade ?? "");
  const [sujeita, setSujeita] = useState(inicial?.sujeita_fator_r ?? true);
  const [qtdSocios, setQtdSocios] = useState(String(inicial?.qtd_socios ?? 1));
  const [contato, setContato] = useState(inicial?.contato ?? "");
  const [pacote, setPacote] = useState<Pacote | "">(inicial?.pacote ?? "");
  const [honorario, setHonorario] = useState(decimalParaEntradaBR(inicial?.honorario_mensal));
  const [inicio, setInicio] = useState(inicial?.inicio_atividade ?? "");
  const [notas, setNotas] = useState(inicial?.notas ?? "");
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const cnpjComErro = cnpj.replace(/\D/g, "").length === 14 && !cnpjValido(cnpj);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErro(null);
    if (!cnpjValido(cnpj)) return setErro("CNPJ inválido.");
    const honorarioDecimal = valorBRParaDecimal(honorario);
    if (honorarioDecimal === null) return setErro("Honorário inválido. Use o formato 1.234,56.");
    setSalvando(true);
    try {
      await onSalvar({
        nome,
        cnpj,
        cnae: cnae || null,
        atividade: atividade || null,
        sujeita_fator_r: sujeita,
        qtd_socios: Number(qtdSocios),
        contato: contato || null,
        pacote: pacote || null,
        honorario_mensal: honorarioDecimal,
        inicio_atividade: inicio || null,
        notas: notas || null,
      });
    } catch (error) {
      setErro(mensagemErro(error));
    } finally {
      setSalvando(false);
    }
  }

  const campo = "mt-1 block w-full rounded border border-zinc-300 px-2 py-1.5";
  return (
    <form onSubmit={onSubmit} className="grid max-w-3xl grid-cols-2 gap-4 text-sm">
      <label className="col-span-2">
        Nome
        <input required value={nome} onChange={(e) => setNome(e.target.value)} className={campo} />
      </label>
      <label>
        CNPJ
        <input
          required
          name="cnpj"
          value={cnpj}
          onChange={(e) => setCnpj(mascararCnpj(e.target.value))}
          aria-invalid={cnpjComErro}
          className={`${campo} ${cnpjComErro ? "border-red-500" : ""}`}
        />
        {cnpjComErro && <span className="text-xs text-red-700">CNPJ inválido</span>}
      </label>
      <label>
        CNAE
        <input value={cnae} onChange={(e) => setCnae(e.target.value)} className={campo} />
      </label>
      <label className="col-span-2">
        Atividade
        <input value={atividade} onChange={(e) => setAtividade(e.target.value)} className={campo} />
      </label>
      <label className="col-span-2 flex items-center gap-2">
        <input
          type="checkbox"
          name="sujeita_fator_r"
          checked={sujeita}
          onChange={(e) => setSujeita(e.target.checked)}
        />
        Atividade sujeita a Fator R (entra na carteira)
      </label>
      <label>
        Início de atividade (mês)
        <input
          type="month"
          name="inicio_atividade"
          value={inicio}
          onChange={(e) => setInicio(e.target.value)}
          className={campo}
        />
      </label>
      <label>
        Quantidade de sócios
        <input
          type="number"
          min={0}
          value={qtdSocios}
          onChange={(e) => setQtdSocios(e.target.value)}
          className={campo}
        />
      </label>
      <label>
        Pacote comercial
        <select
          name="pacote"
          value={pacote}
          onChange={(e) => setPacote(e.target.value as Pacote | "")}
          className={campo}
        >
          <option value="">Sem pacote</option>
          <option value="monitoramento">Monitoramento</option>
          <option value="correcao">Correção</option>
          <option value="retainer">Retainer</option>
        </select>
      </label>
      <label>
        Honorário mensal do pacote (R$)
        <input
          name="honorario"
          inputMode="decimal"
          value={honorario}
          onChange={(e) => setHonorario(e.target.value)}
          placeholder="0,00"
          className={campo}
        />
      </label>
      <label className="col-span-2">
        Contato
        <input value={contato} onChange={(e) => setContato(e.target.value)} className={campo} />
      </label>
      <label className="col-span-2">
        Notas
        <textarea value={notas} onChange={(e) => setNotas(e.target.value)} className={campo} />
      </label>
      {erro && (
        <p role="alert" className="col-span-2 text-red-700">
          {erro}
        </p>
      )}
      <div className="col-span-2">
        <button
          type="submit"
          disabled={salvando}
          className="rounded bg-zinc-900 px-4 py-2 text-white disabled:opacity-60"
        >
          {salvando ? "Salvando..." : rotuloSalvar}
        </button>
      </div>
    </form>
  );
}
