"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { EmpresaForm } from "@/components/empresas/EmpresaForm";
import { criarEmpresa } from "@/lib/api/companies";

export default function NovaEmpresaPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Nova empresa</h1>
      <EmpresaForm
        rotuloSalvar="Cadastrar"
        onSalvar={async (dados) => {
          const empresa = await criarEmpresa(dados);
          await queryClient.invalidateQueries({ queryKey: ["empresas"] });
          router.push(`/empresas/${empresa.id}`);
        }}
      />
    </section>
  );
}
