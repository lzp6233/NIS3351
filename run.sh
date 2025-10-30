#!/bin/bash

# 激活虚拟环境
source venv/bin/activate

# 加载 .env 文件中的环境变量
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✓ 已加载 .env 配置文件"
fi

# 设置默认端口（如果 .env 中未定义）
FRONTEND_PORT=${FRONTEND_PORT:-8000}

# 启动 Flask 服务器（会自动启动 MQTT 客户端）
python backend/app.py &

# 启动传感器模拟器
python simulator/sensor_sim.py &

# 启动门锁模拟器（单把 front_door）
python simulator/lock_sim.py &

# 启动烟雾报警器模拟器
python simulator/smoke_alarm_sim.py &

# 启动前端服务器（使用配置的端口）
cd frontend && python3 -m http.server $FRONTEND_PORT &

echo "系统已启动！"
echo "前端地址: http://localhost:$FRONTEND_PORT"
echo "后端地址: http://localhost:${FLASK_PORT:-5000}"
echo ""
echo "停止所有服务: pkill -f 'python.*backend|python.*simulator|http.server'"
