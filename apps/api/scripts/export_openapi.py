"""Exporta o schema OpenAPI (sem expor /openapi.json em runtime) para gerar tipos do web."""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ENV", "dev")

from fator_r.main import create_app

destino = Path(sys.argv[1])
destino.write_text(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n")
sys.stdout.write(f"OpenAPI exportado para {destino}\n")
