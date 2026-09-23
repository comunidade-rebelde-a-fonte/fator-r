import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { Marca } from "@/components/Marca";

export default function AppLayout({ children }: { children: ReactNode }) {
  return <AppShell marca={<Marca />}>{children}</AppShell>;
}
