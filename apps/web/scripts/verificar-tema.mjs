// Gate do tema (Registro de decisões 2026-09-23): nenhuma cor fixa fora dos tokens de app/globals.css.
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const RAIZES = ["app", "components"];
const PROIBIDO = new RegExp(
  String.raw`\b(bg|text|border|ring|divide|outline|from|to|fill|stroke|placeholder)-(zinc|gray|slate|neutral|stone|red|amber|green|emerald|yellow|blue|orange|sky|indigo|rose|violet|lime|teal|cyan|purple|pink|fuchsia)-\d+|\b(bg|text|border)-(white|black)\b`,
);

function* arquivos(dir) {
  for (const nome of readdirSync(dir)) {
    const caminho = path.join(dir, nome);
    if (statSync(caminho).isDirectory()) yield* arquivos(caminho);
    else if (/\.(tsx?|css)$/.test(nome)) yield caminho;
  }
}

const achados = [];
for (const raiz of RAIZES) {
  for (const arquivo of arquivos(raiz)) {
    readFileSync(arquivo, "utf8")
      .split("\n")
      .forEach((linha, i) => {
        if (PROIBIDO.test(linha)) achados.push(`${arquivo}:${i + 1}: ${linha.trim()}`);
      });
  }
}

if (achados.length) {
  console.error(`Cor fora do tema (use os tokens de app/globals.css):\n${achados.join("\n")}`);
  process.exit(1);
}
