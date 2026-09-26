#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
curl --fail --silent --show-error --max-time 5 http://localhost:5678/healthz >/dev/null
curl --fail --silent --show-error --max-time 5 http://localhost:8090/healthz >/dev/null
printf 'n8n y el banco local responden correctamente.\n'
