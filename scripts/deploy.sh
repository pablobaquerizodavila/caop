#!/usr/bin/env bash
# Despliega/actualiza CAOP en el servidor. Ejecutar EN 192.168.0.7.
# Uso: ./deploy.sh [directorio]   (por defecto: $HOME/caop)
set -euo pipefail

REPO="https://github.com/pablobaquerizodavila/caop.git"
DIR="${1:-$HOME/caop}"

echo ">> Directorio de despliegue: $DIR"
if [ ! -d "$DIR/.git" ]; then
  echo ">> Clonando repositorio..."
  git clone "$REPO" "$DIR"
else
  echo ">> Actualizando repositorio..."
  git -C "$DIR" fetch --all --prune
  git -C "$DIR" checkout main
  git -C "$DIR" pull --ff-only
fi

cd "$DIR"

if [ ! -f .env ]; then
  echo ">> Creando .env desde .env.example (revisa/cambia las contraseñas)"
  cp .env.example .env
fi

echo ">> Levantando el stack (build + up)..."
docker compose pull --quiet || true
docker compose up -d --build

echo ">> Esperando readiness del backend..."
for i in $(seq 1 60); do
  if curl -fsS http://192.168.0.7:8000/api/v1/health/ready >/dev/null 2>&1; then
    echo ">> Backend READY"
    break
  fi
  sleep 5
done

echo ">> Estado de los servicios:"
docker compose ps
echo ">> Health:"
curl -s http://192.168.0.7:8000/api/v1/health || true
echo
echo ">> Listo. URLs:"
echo "   API:        http://192.168.0.7:8000/docs"
echo "   Frontend:   http://192.168.0.7:3000"
echo "   Keycloak:   http://192.168.0.7:8080"
echo "   Temporal:   http://192.168.0.7:8081"
echo "   MinIO:      http://192.168.0.7:9001"
echo "   Mailpit:    http://192.168.0.7:8025"
