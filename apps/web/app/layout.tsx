import type { Metadata } from "next";
import "./globals.css";
import { Disclaimer } from "@/components/Disclaimer";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Fator R",
  description: "Monitoramento de Fator R para escritórios de contabilidade",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <Providers>
          <div className="flex flex-1 flex-col">{children}</div>
          <Disclaimer />
        </Providers>
      </body>
    </html>
  );
}
