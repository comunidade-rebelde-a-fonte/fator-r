"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";

import { EmpresaForm } from "@/components/empresas/EmpresaForm";
import { Carregando, Erro } from "@/components/ui/Estado";
import { atualizarEmpresa, obterEmpresa } from "@/lib/api/companies";

export default function EditarEmpresaPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const empresa = useQuery({ queryKey: ["empresa", id], queryFn: () => obterEmpresa(id) });

  if (empresa.isPending) return <Carregando />;
  if (empresa.isError) return <Erro texto="Empresa não encontrada." />;
  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Editar {empresa.data.nome}</h1>
      <EmpresaForm
        inicial={empresa.data}
        rotuloSalvar="Salvar alterações"
        onSalvar={async (dados) => {
          await atualizarEmpresa(id, dados);
          await queryClient.invalidateQueries({ queryKey: ["empresas"] });
          await queryClient.invalidateQueries({ queryKey: ["empresa", id] });
          router.push(`/empresas/${id}`);
        }}
      />
    </section>
  );
}
