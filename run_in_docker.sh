#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

# WordPress-Zugangsdaten aus lokaler .env-Datei laden (nicht ins Repo committen!).
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "Fehler: GH_TOKEN fehlt. Bitte GH_TOKEN in .env oder in der Host-Umgebung setzen." >&2
  exit 1
fi

docker build -t ingolstadt-chapter-bot .

docker run --rm \
  -e GH_TOKEN="$GH_TOKEN" \
  -e WP_USER="${WP_USER:?WP_USER muss in .env gesetzt sein}" \
  -e WP_APP_PASSWORD="${WP_APP_PASSWORD:?WP_APP_PASSWORD muss in .env gesetzt sein}" \
  ingolstadt-chapter-bot
