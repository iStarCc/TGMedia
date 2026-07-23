#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="${ROOT_DIR}/Apps/tgmedia"
FRONTEND_DIR="${ROOT_DIR}/frontend"
BACKEND_DIR="${ROOT_DIR}/backend"

FNPACK="${FNPACK_BIN:-}"
if [ -z "${FNPACK}" ]; then
    if command -v fnpack &> /dev/null; then
        FNPACK="fnpack"
    elif [ -x "${ROOT_DIR}/fnpack" ]; then
        FNPACK="${ROOT_DIR}/fnpack"
    fi
fi

echo "=== TGMedia Build Script ==="

APP_VERSION=$(python3 -c "import json; print(json.load(open('${ROOT_DIR}/version.json'))['version'])")
echo "Version: ${APP_VERSION}"

cp "${ROOT_DIR}/version.json" "${BACKEND_DIR}/version.json"
cp "${ROOT_DIR}/version.json" "${FRONTEND_DIR}/public/version.json"
sed -i '' "s/^version=.*/version=${APP_VERSION}/" "${APP_DIR}/manifest"
sed -i '' "s/<meta name=\"app-version\" content=\"[^\"]*\"/<meta name=\"app-version\" content=\"${APP_VERSION}\"/" "${FRONTEND_DIR}/index.html"

# 1. 前端构建
echo "[1/4] Building frontend..."
cd "${FRONTEND_DIR}"
npm install --silent
VITE_BASE_PATH="/app/tgmedia/" npm run build

# 2. 复制前端产物
echo "[2/4] Copying frontend assets..."
rm -rf "${APP_DIR}/app/server/www"
mkdir -p "${APP_DIR}/app/server/www"
cp -r "${FRONTEND_DIR}/dist/"* "${APP_DIR}/app/server/www/"

# 3. 复制后端代码
echo "[3/4] Copying backend..."
rm -rf "${APP_DIR}/app/server/app"
cp -r "${BACKEND_DIR}/app" "${APP_DIR}/app/server/app"
cp "${BACKEND_DIR}/requirements.txt" "${APP_DIR}/app/server/requirements.txt"
cp "${BACKEND_DIR}/pyproject.toml" "${APP_DIR}/app/server/pyproject.toml"
cp "${ROOT_DIR}/version.json" "${APP_DIR}/app/server/version.json"
cp "${ROOT_DIR}/version.json" "${APP_DIR}/app/server/www/version.json"

# 4. fnpack 打包
echo "[4/4] Building fpk package..."
if [ -n "${FNPACK}" ]; then
    cd "${APP_DIR}"
    "${FNPACK}" build
    echo "=== Build complete ==="
    ls -lh "${APP_DIR}"/*.fpk 2>/dev/null
else
    echo "=== fnpack not found, skipping fpk packaging ==="
    echo "=== Frontend + Backend copied to ${APP_DIR}/app/server/ ==="
    echo "=== Install fnpack from https://static2.fnnas.com/fnpack/ ==="
fi
