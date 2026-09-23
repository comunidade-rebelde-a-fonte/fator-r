"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Botao } from "@/components/ui/Botao";
import { classesCampo } from "@/components/ui/Campo";
import { TituloPagina } from "@/components/ui/TituloPagina";
import { ApiError } from "@/lib/api";
import { login, ME_QUERY_KEY } from "@/lib/auth";

function mensagemDeErro(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "E-mail ou senha inválidos.";
    if (error.status === 429) return "Muitas tentativas. Aguarde alguns minutos.";
    if (error.status === 422) return "Informe um e-mail válido e a senha.";
  }
  return "Não foi possível entrar agora. Tente novamente.";
}

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      const me = await login(email, senha);
      queryClient.setQueryData(ME_QUERY_KEY, me);
      router.replace("/carteira");
    } catch (error) {
      setErro(mensagemDeErro(error));
      setEnviando(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center bg-[radial-gradient(circle_at_18%_0%,rgba(255,134,25,.05),transparent_32%),radial-gradient(circle_at_82%_0%,rgba(255,41,61,.04),transparent_32%)] p-6">
      <form
        onSubmit={onSubmit}
        className="border-line bg-panel w-full max-w-sm space-y-4 rounded-[10px] border p-6 shadow-[0_20px_60px_-30px_rgba(0,0,0,.8),inset_0_1px_0_rgba(255,255,255,.04)]"
      >
        <div>
          <TituloPagina>Fator R</TituloPagina>
          <p className="text-muted mt-2 text-sm">Acesso do escritório</p>
        </div>
        <label className="block text-sm">
          E-mail
          <input
            type="email"
            name="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={`mt-1 w-full px-3 py-2 ${classesCampo}`}
          />
        </label>
        <label className="block text-sm">
          Senha
          <input
            type="password"
            name="senha"
            autoComplete="current-password"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            className={`mt-1 w-full px-3 py-2 ${classesCampo}`}
          />
        </label>
        {erro && (
          <p role="alert" className="text-danger-soft text-sm">
            {erro}
          </p>
        )}
        <Botao type="submit" tamanho="lg" disabled={enviando} className="w-full">
          {enviando ? "Entrando..." : "Entrar"}
        </Botao>
      </form>
    </main>
  );
}
