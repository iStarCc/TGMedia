#!/bin/bash
#
# TGMedia 开发环境一键启动脚本
# 用法: ./scripts/dev.sh [stop]
#

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

BACKEND_PORT=8000
FRONTEND_PORT=5173

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[TGMedia]${NC} $1"; }
warn() { echo -e "${YELLOW}[TGMedia]${NC} $1"; }
err()  { echo -e "${RED}[TGMedia]${NC} $1"; }

kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti ":${port}" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        warn "端口 ${port} 被占用，正在清理 (PID: ${pids})..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 0.5
    fi
}

stop_all() {
    log "停止所有服务..."
    kill_port ${BACKEND_PORT}
    kill_port ${FRONTEND_PORT}
    log "已停止"
    exit 0
}

if [ "$1" = "stop" ]; then
    stop_all
fi

echo -e "${CYAN}"
echo "  ╔════════════════════════════════╗"
echo "  ║     TGMedia Dev Environment    ║"
echo "  ╚════════════════════════════════╝"
echo -e "${NC}"

# 清理端口
kill_port ${BACKEND_PORT}
kill_port ${FRONTEND_PORT}

# 创建运行时目录
DATA_ROOT="${ROOT_DIR}/.data"
mkdir -p "${DATA_ROOT}"/{data,var,etc}

# 检查后端虚拟环境
if [ ! -d "${BACKEND_DIR}/.venv" ]; then
    log "创建 Python 虚拟环境..."
    python3 -m venv "${BACKEND_DIR}/.venv"
    log "安装后端依赖..."
    "${BACKEND_DIR}/.venv/bin/pip" install -q -r "${BACKEND_DIR}/requirements.txt"
fi

# 检查前端依赖
if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
    log "安装前端依赖..."
    cd "${FRONTEND_DIR}" && npm install --silent
fi

# 启动后端
log "启动后端 (http://127.0.0.1:${BACKEND_PORT})..."
cd "${BACKEND_DIR}"
.venv/bin/python -m uvicorn app.main:app \
    --host 127.0.0.1 --port ${BACKEND_PORT} --reload \
    > "${DATA_ROOT}/backend.log" 2>&1 &
BACKEND_PID=$!

# 等待后端就绪
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:${BACKEND_PORT}/api/health" > /dev/null 2>&1; then
        break
    fi
    sleep 0.3
done

if curl -s "http://127.0.0.1:${BACKEND_PORT}/api/health" > /dev/null 2>&1; then
    log "后端已就绪 (PID: ${BACKEND_PID})"
else
    err "后端启动超时，查看日志: ${DATA_ROOT}/backend.log"
    exit 1
fi

# 启动前端
log "启动前端 (http://127.0.0.1:${FRONTEND_PORT})..."
cd "${FRONTEND_DIR}"
npx vite --host 127.0.0.1 --port ${FRONTEND_PORT} \
    > "${DATA_ROOT}/frontend.log" 2>&1 &
FRONTEND_PID=$!

sleep 1
if kill -0 ${FRONTEND_PID} 2>/dev/null; then
    log "前端已就绪 (PID: ${FRONTEND_PID})"
else
    err "前端启动失败，查看日志: ${DATA_ROOT}/frontend.log"
    exit 1
fi

echo ""
echo -e "${GREEN}==============================${NC}"
echo -e "  前端: ${CYAN}http://127.0.0.1:${FRONTEND_PORT}${NC}"
echo -e "  后端: ${CYAN}http://127.0.0.1:${BACKEND_PORT}${NC}"
echo -e "  日志: ${DATA_ROOT}/*.log"
echo -e "${GREEN}==============================${NC}"
echo ""
echo -e "  停止: ${YELLOW}./scripts/dev.sh stop${NC}"
echo ""

# 前台等待，Ctrl+C 时清理
trap 'echo ""; log "正在停止..."; kill_port ${BACKEND_PORT}; kill_port ${FRONTEND_PORT}; log "已停止"; exit 0' INT TERM

wait
