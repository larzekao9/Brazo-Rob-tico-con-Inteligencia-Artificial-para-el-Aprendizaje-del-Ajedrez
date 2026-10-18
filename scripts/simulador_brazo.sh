#!/usr/bin/env bash
# Arranca el simulador del brazo con el Python del entorno conda `ajedrez` (el que trae PyBullet y python-chess).
# Uso: ./scripts/simulador_brazo.sh [opciones de simulador_brazo.py, por ejemplo --escala-tiempo 5]
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENTORNO="${ENTORNO_CONDA:-ajedrez}"

buscar_python() {
  if [[ -n "${PYTHON_SIMULADOR:-}" ]]; then echo "$PYTHON_SIMULADOR"; return; fi
  if [[ "${CONDA_DEFAULT_ENV:-}" == "$ENTORNO" && -n "${CONDA_PREFIX:-}" && -x "$CONDA_PREFIX/bin/python" ]]; then
    echo "$CONDA_PREFIX/bin/python"; return
  fi
  local bases=()
  if command -v conda >/dev/null 2>&1; then bases+=("$(conda info --base 2>/dev/null || true)"); fi
  bases+=("/opt/homebrew/Caskroom/miniforge/base" "$HOME/miniforge3" "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/mambaforge")
  for base in "${bases[@]}"; do
    if [[ -n "$base" && -x "$base/envs/$ENTORNO/bin/python" ]]; then echo "$base/envs/$ENTORNO/bin/python"; return; fi
  done
}

PYTHON="$(buscar_python)"
if [[ -z "$PYTHON" ]]; then
  echo "No encontré el entorno conda '$ENTORNO'. Creálo con environment.yml, activalo (conda activate $ENTORNO)" >&2
  echo "o indicá el Python con PYTHON_SIMULADOR=/ruta/al/python ./scripts/simulador_brazo.sh" >&2
  exit 1
fi

cd "$RAIZ"
export KMP_DUPLICATE_LIB_OK=TRUE
exec "$PYTHON" scripts/simulador_brazo.py "$@"
