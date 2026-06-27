#!/usr/bin/env bash
# Corrida diaria de StrateX: scraping del DOF + análisis por IA.
# Pensado para ejecutarse vía cron o launchd. Registra la salida en logs/.
set -euo pipefail

# Raíz del proyecto = carpeta padre de este script (resuelve symlinks).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y-%m-%d)"
LOG_FILE="$LOG_DIR/pipeline_${STAMP}.log"

# Usa el intérprete del entorno virtual del proyecto.
PYTHON="$PROJECT_DIR/.venv/bin/python"

{
  echo "===== Corrida $(date '+%Y-%m-%d %H:%M:%S') ====="
  "$PYTHON" run_pipeline.py 0
} >> "$LOG_FILE" 2>&1
