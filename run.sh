#!/bin/bash

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "NIS3351 智能家居监控系统启动脚本"
echo "========================================"

# 检查并激活虚拟环境（支持多种虚拟环境名称）
VENV_ACTIVATED=0

if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ 虚拟环境 'venv' 已激活${NC}"
    VENV_ACTIVATED=1
elif [ -d "database" ]; then
    source database/bin/activate
    echo -e "${GREEN}✓ 虚拟环境 'database' 已激活${NC}"
    VENV_ACTIVATED=1
elif [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}✓ 检测到已激活的虚拟环境: $VIRTUAL_ENV${NC}"
    VENV_ACTIVATED=1
fi

if [ $VENV_ACTIVATED -eq 0 ]; then
    echo -e "${RED}✗ 未检测到虚拟环境！${NC}"
    echo ""
    echo "请先创建并激活虚拟环境，然后再运行此脚本："
    echo -e "${YELLOW}  python3 -m venv database${NC}"
    echo -e "${YELLOW}  source database/bin/activate${NC}"
    echo -e "${YELLOW}  pip install -r requirements.txt${NC}"
    exit 1
fi

# 检查关键依赖是否安装
python -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Python 依赖未安装！${NC}"
    echo ""
    echo "请先安装依赖："
    echo -e "${YELLOW}  pip install -r requirements.txt${NC}"
    exit 1
fi

# 加载 .env 文件中的环境变量
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✓ 已加载 .env 配置文件${NC}"
else
    echo -e "${YELLOW}⚠ .env 文件不存在，使用默认配置${NC}"
fi

# 设置默认端口（如果 .env 中未定义）
FRONTEND_PORT=${FRONTEND_PORT:-8000}
FLASK_PORT=${FLASK_PORT:-5000}

# 检查端口占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # 端口被占用
    else
        return 1  # 端口空闲
    fi
}

# 检查后端端口
if check_port $FLASK_PORT; then
    echo -e "${RED}✗ 端口 $FLASK_PORT 已被占用！${NC}"
    echo "请先停止占用该端口的服务，或修改 .env 文件中的 FLASK_PORT"
    exit 1
fi

# 检查前端端口
if check_port $FRONTEND_PORT; then
    echo -e "${RED}✗ 端口 $FRONTEND_PORT 已被占用！${NC}"
    echo "请先停止占用该端口的服务："
    echo -e "${YELLOW}  pkill -f 'http.server'${NC}"
    echo "或修改 .env 文件中的 FRONTEND_PORT"
    exit 1
fi

echo ""
echo "正在启动服务..."

# 启动 Flask 服务器（会自动启动 MQTT 客户端）
python backend/app.py &
echo -e "${GREEN}✓ 后端服务已启动 (PID: $!)${NC}"

# 等待一秒确保后端启动
sleep 1

# 启动传感器模拟器
python simulator/sensor_sim.py &
echo -e "${GREEN}✓ 传感器模拟器已启动 (PID: $!)${NC}"

# 启动门锁模拟器（单把 front_door）
python simulator/lock_sim.py &
echo -e "${GREEN}✓ 门锁模拟器已启动 (PID: $!)${NC}"

# 启动烟雾报警器模拟器
python simulator/smoke_alarm_sim.py &
echo -e "${GREEN}✓ 烟雾报警器模拟器已启动 (PID: $!)${NC}"

# 启动灯具模拟器
python simulator/lighting_sim.py &
echo -e "${GREEN}✓ 灯具模拟器已启动 (PID: $!)${NC}"

# 启动前端服务器（使用配置的端口）
cd frontend && python3 -m http.server $FRONTEND_PORT &
echo -e "${GREEN}✓ 前端服务已启动 (PID: $!)${NC}"
cd ..

echo ""
echo "========================================"
echo -e "${GREEN}✓ 系统启动成功！${NC}"
echo "========================================"
echo -e "前端地址: ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
echo -e "后端地址: ${GREEN}http://localhost:$FLASK_PORT${NC}"
echo ""
echo -e "${YELLOW}停止所有服务:${NC}"
echo "  pkill -f 'python.*backend|python.*simulator|http.server'"
echo "========================================"
