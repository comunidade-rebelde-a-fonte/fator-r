import { existsSync } from "node:fs";
import path from "node:path";

const LOGO = "/brand/logo.svg";

/** Logo opcional do escritório: usa `public/brand/logo.svg` se existir; senão, o nome em Oswald. */
export function Marca() {
  if (existsSync(path.join(process.cwd(), "public", LOGO))) {
    // eslint-disable-next-line @next/next/no-img-element -- SVG local e opcional; next/image não agrega aqui
    return <img src={LOGO} alt="Fator R" className="h-7 w-auto" />;
  }
  return (
    <span className="font-display text-lg tracking-wide uppercase">
      Fator <span className="text-accent">R</span>
    </span>
  );
}
