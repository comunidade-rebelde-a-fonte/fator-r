"use client";

import { useState, type FormEvent } from "react";

import { Botao } from "@/components/ui/Botao";
import { classesCampo } from "@/components/ui/Campo";
import { ApiError } from "@/lib/api";
import type { CompanyIn, CompanyOut, Pacote } from "@/lib/api/types";
import { cnpjValido, mascararCnpj } from "@/lib/cnpj";
import { decimalParaEntradaBR, valorBRParaDecimal } from "@/lib/format";

/** Valores iniciais: a ficha inteira (edição) ou parte dela (cadastro pelo extrato, M8). */
export type ValoresIniciaisEmpresa = Partial<Omit<CompanyOut, "sujeita_fator_r">> & {
  /** `null`: o analista precisa escolher antes de salvar. */
  sujeita_fator_r?: boolean | null;
};

type Props = {
  inicial?: ValoresIniciaisEmpresa;
  /** CNPJ travado: é a chave do vínculo com o extrato. */
  cnpjSomenteLeitura?: boolean;
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

export function EmpresaForm({ inicial, cnpjSomenteLeitura, rotuloSalvar, onSalvar }: Props) {
  const [nome, setNome] = useState(inicial?.nome ?? "");
  const [cnpj, setCnpj] = useState(inicial?.cnpj_formatado ?? "");
  const [cnae, setCnae] = useState(inicial?.cnae ?? "");
  const [atividade, setAtividade] = useState(inicial?.atividade ?? "");
  const [sujeita, setSujeita] = useState<boolean | null>(
    inicial?.sujeita_fator_r === undefined ? true : inicial.sujeita_fator_r,
  );
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
    if (sujeita === null) return setErro("Informe se a atividade é sujeita a Fator R.");
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

  const campo = `mt-1 block w-full px-2 py-1.5 ${classesCampo}`;
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
          readOnly={cnpjSomenteLeitura}
          onChange={(e) => setCnpj(mascararCnpj(e.target.value))}
          aria-invalid={cnpjComErro}
          className={`${campo} ${cnpjSomenteLeitura ? "read-only:bg-panel read-only:text-muted" : ""}`}
        />
        {cnpjComErro && <span className="text-danger-soft text-xs">CNPJ inválido</span>}
      </label>
      <label>
        CNAE
        <input value={cnae} onChange={(e) => setCnae(e.target.value)} className={campo} />
      </label>
      <label className="col-span-2">
        Atividade
        <input value={atividade} onChange={(e) => setAtividade(e.target.value)} className={campo} />
      </label>
      <fieldset className="col-span-2">
        <legend>Atividade sujeita a Fator R (entra na carteira)</legend>
        <div className="mt-1 flex gap-4">
          {[
            { valor: true, rotulo: "Sim" },
            { valor: false, rotulo: "Não" },
          ].map((opcao) => (
            <label key={opcao.rotulo} className="flex items-center gap-1">
              <input
                type="radio"
                name="sujeita_fator_r"
                value={String(opcao.valor)}
                checked={sujeita === opcao.valor}
                onChange={() => setSujeita(opcao.valor)}
              />
              {opcao.rotulo}
            </label>
          ))}
        </div>
        {sujeita === null && (
          <span className="text-accent-soft text-xs">
            O extrato não diz se a atividade é sujeita a Fator R. Escolha antes de salvar.
          </span>
        )}
      </fieldset>
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
        <p role="alert" className="text-danger-soft col-span-2">
          {erro}
        </p>
      )}
      <div className="col-span-2">
        <Botao type="submit" tamanho="lg" disabled={salvando || sujeita === null}>
          {salvando ? "Salvando..." : rotuloSalvar}
        </Botao>
      </div>
    </form>
  );
}
