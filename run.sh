#!/bin/bash

# 激活虚拟环境
source venv/bin/activate

# 启动 Flask 服务器（会自动启动 MQTT 客户端）
python backend/app.py &

# 启动传感器模拟器
python simulator/sensor_sim.py &

# 启动门锁模拟器（单把 front_door）
python simulator/lock_sim.py &

# 启动前端服务器
cd frontend && python3 -m http.server 8000 &

echo "系统已启动！"
echo "前端地址: http://localhost:8000"
echo "后端地址: http://localhost:5000"
echo ""
echo "停止所有服务: pkill -f 'python.*backend|python.*simulator|http.server'"
