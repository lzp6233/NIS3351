# NIS3351 智能家居监控系统

基于 IoT 技术的温湿度实时监控系统，支持多设备、多传感器，实时数据采集与可视化。

---

#### 当前的问题
+ 与GaussDB通信时的 SASL认证问题



## 📋 系统架构

```
传感器模拟器 → MQTT Broker → MQTT 客户端 → GaussDB 数据库
                                    ↓
                            Flask Web 服务器
                                    ↓
                            前端界面（ECharts）
```

---

## 📦 依赖安装

### 1. 系统依赖（必须）

#### 在 openEuler / CentOS 上：

```bash
# 更新系统
sudo yum update -y

# 安装基础工具
sudo yum install -y gcc make cmake git wget curl

# 安装 Python 开发包
sudo yum install -y python3 python3-devel python3-pip

# 安装数据库开发库（用于 psycopg2）
sudo yum install -y openssl-devel libpq-devel

# 安装 MQTT Broker
sudo yum install -y mosquitto
```

### 2. GaussDB / openGauss 数据库

#### 安装 GaussDB（如果未安装，默认已经安装）

参考官方文档：https://opengauss.org/zh/download/

或使用一键安装脚本（openGauss Lite）：

```bash
# 下载安装包
wget https://opengauss.obs.cn-south-1.myhuaweicloud.com/latest/arm/openGauss-Lite-5.0.1-openEuler-aarch64.tar.gz

# 解压并安装
tar -xzf openGauss-Lite-5.0.1-openEuler-aarch64.tar.gz
cd openGauss-Lite-5.0.1-openEuler-aarch64
sudo bash install.sh
```

#### 配置 GaussDB 环境变量

编辑 `~/.bashrc`，添加以下内容：

```bash
# GaussDB 环境变量
export GAUSSDB_HOME=/usr/local/opengauss
export PATH=$GAUSSDB_HOME/bin:$PATH
export LD_LIBRARY_PATH=$GAUSSDB_HOME/lib:$LD_LIBRARY_PATH
```

应用配置：
```bash
source ~/.bashrc
```

#### 启动 GaussDB

```bash
# 方法 1：使用 systemctl（如果配置了服务）
sudo systemctl start gaussdb

# 方法 2：切换到 opengauss 用户手动启动 （官方文档）
su - opengauss
gs_ctl start -D /var/lib/opengauss/data

# 验证是否运行
ps -ef | grep gaussdb
```

### 3. MQTT Broker（Mosquitto）

#### 安装 Mosquitto

```bash
# openEuler / CentOS
sudo yum install -y mosquitto

# Ubuntu / Debian
sudo apt-get install -y mosquitto mosquitto-clients
```

#### 启动 Mosquitto

```bash
# 启动服务
sudo systemctl start mosquitto

# 设置开机自启
sudo systemctl enable mosquitto

# 查看状态
sudo systemctl status mosquitto

# 验证端口监听
netstat -tlnp | grep 1883
```

#### 测试 MQTT

```bash
# 终端 1：订阅消息
mosquitto_sub -h localhost -t test/topic

# 终端 2：发布消息
mosquitto_pub -h localhost -t test/topic -m "Hello MQTT"
```

---

## 🚀 项目安装与配置

### 1. 克隆项目

```bash
cd ~
git clone <项目地址>
cd NIS3351
```

### 2. 创建 Python 虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip
```

### 3. 安装 Python 依赖

```bash
# 安装所有依赖
pip install -r requirements.txt
```

**主要依赖包**：
- Flask 2.3.3 - Web 框架
- Flask-SocketIO 5.5.1 - WebSocket 实时通信
- Flask-CORS 4.0.0 - 跨域支持
- paho-mqtt 1.6.1 - MQTT 客户端
- psycopg2-binary 2.9.9 - PostgreSQL/GaussDB 驱动
- python-dotenv 1.0.0 - 环境变量管理

### 4. 配置环境变量

```bash
touch .env
```
写入：
DB_USER=
DB_PASSWORD=
DB_ADMIN_USER=opengauss
DB_ADMIN_PASSWORD=

**必须修改的配置**：

```bash
# 数据库配置
DB_USER=your_username              # 你的数据库用户名
DB_PASSWORD=your_password          # 你的数据库密码
DB_ADMIN_USER=opengauss            # GaussDB 管理员用户
DB_ADMIN_PASSWORD=admin_password   # 管理员密码

# 数据库连接信息
DB_HOST=127.0.0.1
DB_PORT=7654                       # 根据实际端口修改
DB_NAME=smart_home
```

### 5. 初始化数据库

```bash
# 给脚本添加执行权限
chmod +x setup_database.sh

# 运行初始化脚本
./setup_database.sh
```

脚本会自动：
- ✅ 读取 .env 配置
- ✅ 创建数据库
- ✅ 创建数据表
- ✅ 插入测试数据
- ✅ 配置用户权限

---

## ▶️ 启动系统

### 一键启动（推荐）

```bash
# 给启动脚本添加执行权限
chmod +x run.sh

# 启动所有服务
sh run.sh
```

启动后会运行以下服务：
- MQTT 客户端（后台）
- Flask Web 服务器（端口 5000）
- 传感器模拟器（后台）
- 前端 HTTP 服务器（端口 8000）

### 手动启动（逐个启动）

```bash
# 激活虚拟环境
source venv/bin/activate

# 终端 1：启动 MQTT 客户端
python backend/mqtt_client.py

# 终端 2：启动 Flask 服务器
python backend/app.py

# 终端 3：启动传感器模拟器
python simulator/sensor_sim.py

# 终端 4：启动前端服务器
cd frontend && python3 -m http.server 8000
```

### 访问系统

- **前端界面**：http://localhost:8000
- **后端 API**：http://localhost:5000

**从其他设备访问**（将 IP 替换为实际地址）：
- http://192.168.x.x:8000

---

## 🛑 停止系统

```bash
# 停止所有后台服务
pkill -f 'python.*backend|python.*simulator|http.server'
```

---

## 📡 API 接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/` | API 信息 |
| GET | `/devices` | 获取所有设备列表 |
| GET | `/history` | 获取所有历史数据 |
| GET | `/history/<device_id>` | 获取指定设备历史数据 |
| GET | `/latest/<device_id>` | 获取指定设备最新数据 |

**示例**：
```bash
# 获取设备列表
curl http://localhost:5000/devices

# 获取 room1 的历史数据
curl http://localhost:5000/history/room1
```

---

## 🗄️ 数据库表结构

### temperature_humidity_data

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键，自增 |
| device_id | VARCHAR(50) | 设备标识（如 room1, room2） |
| temperature | FLOAT | 温度值（°C） |
| humidity | FLOAT | 湿度值（%） |
| timestamp | TIMESTAMP | 记录时间 |

---

## 🔧 常见问题

### 1. GaussDB 连接失败

**问题**：`connection refused` 或 `could not connect to server`

**解决方案**：
```bash
# 检查 GaussDB 是否运行
ps -ef | grep gaussdb

# 检查端口
netstat -tlnp | grep 7654

# 启动 GaussDB
su - opengauss
gs_ctl start -D /var/lib/opengauss/data
```

### 2. MQTT 连接失败

**问题**：`Connection refused on port 1883`

**解决方案**：
```bash
# 安装 Mosquitto
sudo yum install -y mosquitto

# 启动服务
sudo systemctl start mosquitto

# 验证
netstat -tlnp | grep 1883
```

### 3. 虚拟环境问题

**问题**：`pip` 命令指向系统 Python

**解决方案**：
```bash
# 删除旧虚拟环境
rm -rf venv

# 重新创建
python3 -m venv venv
source venv/bin/activate

# 验证
which pip  # 应该显示 venv/bin/pip
```

### 4. 端口被占用

**问题**：`Address already in use`

**解决方案**：
```bash
# 查找占用端口的进程
netstat -tlnp | grep 5000

# 杀死进程
kill <PID>
```

---

## 📚 项目结构

```
NIS3351/
├── .env.example          # 环境变量模板
├── .env                  # 实际配置（不提交到 Git）
├── .gitignore            # Git 忽略文件
├── readme.md             # 项目文档
├── requirements.txt      # Python 依赖
├── run.sh                # 一键启动脚本
├── setup_database.sh     # 数据库初始化脚本
├── init_db.sql           # SQL 初始化脚本
├── backend/              # 后端代码
│   ├── app.py            # Flask 应用
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库操作
│   └── mqtt_client.py    # MQTT 客户端
├── frontend/             # 前端代码
│   ├── index.html        # 主页面
│   ├── main.js           # JavaScript 逻辑
│   └── style.css         # 样式
└── simulator/            # 传感器模拟器
    ├── config.py         # 模拟器配置
    └── sensor_sim.py     # 模拟器主程序
```

---

## 🎯 快速开始清单

- [ ] 安装系统依赖（gcc, python3-dev, libpq-dev）
- [ ] 安装并启动 GaussDB
- [ ] 配置 GaussDB 环境变量
- [ ] 安装并启动 Mosquitto
- [ ] 创建 Python 虚拟环境
- [ ] 安装 Python 依赖
- [ ] 创建并配置 .env 文件
- [ ] 初始化数据库（运行 setup_database.sh）
- [ ] 启动系统（运行 run.sh）
- [ ] 访问 http://localhost:8000

---

## 📖 参考文档

- [GaussDB/openGauss 官方文档](https://opengauss.org/)
- [Mosquitto 文档](https://mosquitto.org/)
- [Flask 文档](https://flask.palletsprojects.com/)
- [MQTT 协议](https://mqtt.org/)
