# NIS3351 智能家居监控系统

基于 IoT 技术的温湿度实时监控系统，支持多设备、多传感器，实时数据采集与可视化。

---

## 🐛 已解决的问题

### 1. 虚拟环境损坏
**问题**：多个包的 METADATA 文件丢失，导致 `pip install` 失败  
**解决**：重建虚拟环境
```bash
mv venv venv_backup
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. openGauss SCRAM-SHA-256 认证问题
**问题**：psycopg3 不支持 openGauss 的 SCRAM-SHA-256 认证机制  
**解决**：切换到 openGauss 官方驱动 `py-opengauss`
```bash
pip install py-opengauss
```

### 3. py-opengauss API 适配
**问题**：py-opengauss API 与 psycopg2/psycopg3 不同  
**关键差异**：
- 连接：`py_opengauss.open("opengauss://user:pass@host:port/db")`
- 参数占位符：使用 `$1, $2, $3`（而非 `%s`）
- 查询：`conn.prepare(sql)` 返回可调用的 statement
- 无需 `cursor()`：直接使用 connection 对象
- 无需 `commit()`：自动提交

### 4. MQTT Client API 弃用
**问题**：paho-mqtt 2.x 弃用旧 API  
**解决**：更新为新 API
```python
# 旧版
client = mqtt.Client()

# 新版
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
```

### 5. 网络配置问题
**问题**：缺少默认网关，无法访问外网  
**解决**：添加网关配置到 `/etc/sysconfig/network-scripts/ifcfg-eth0`
```bash
GATEWAY=192.168.10.101
DNS1=8.8.8.8
```



## 📋 系统架构

```
传感器模拟器/门锁模拟器 → MQTT Broker → MQTT 客户端 → GaussDB 数据库
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

# 安装数据库开发库（用于编译 py-opengauss）
sudo yum install -y openssl-devel libpq-devel

# 安装 MQTT Broker
sudo yum install -y mosquitto
```

### 2. GaussDB / openGauss 数据库

#### 在 macOS 上使用 Docker 启动 openGauss（推荐）

先安装 Docker Desktop，然后在项目根目录执行：

```bash
docker compose up -d opengauss
# 首次启动等待健康检查通过（约 30-60 秒）
```

容器信息：
- 映射端口：本机 7654 -> 容器 5432（已与项目默认配置一致）
- 管理员用户：`gaussdb`（镜像默认）
- 管理员密码：`StrongPassw0rd!`

配置 .env（示例）：
```bash
DB_HOST=127.0.0.1
DB_PORT=7654
DB_NAME=smart_home
DB_ADMIN_USER=gaussdb
DB_ADMIN_PASSWORD=StrongPassw0rd!
DB_USER=app_user
DB_PASSWORD=app_password
```

准备就绪后，执行初始化脚本：

```bash
./setup_database.sh
```

#### 在华为鲲鹏板上原生部署 openGauss（无 Docker）

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

> 完成数据库安装后，按 `.env` 中的参数执行 `./setup_database.sh` 初始化表结构与示例数据（已包含门锁表）。

### 3. 本地开发数据库选择

默认使用 sqlite（零依赖）：

- 已将 `backend/config.py` 的默认 `DB_TYPE` 设为 `sqlite`，无需安装 openGauss 即可运行；
- 首次运行会自动创建所需表（含门锁表），无需执行 `init_db.sql`；
- 若你需要切换到 openGauss（如在鲲鹏板上或本机 Docker），将 `.env` 中 `DB_TYPE=opengauss` 并按照上文安装步骤执行 `./setup_database.sh` 即可。

### 4. MQTT Broker（Mosquitto）

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
- paho-mqtt 2.1.0 - MQTT 客户端
- py-opengauss 1.3.10 - openGauss 官方驱动（支持 SCRAM-SHA-256 认证）
- python-dotenv 1.0.0 - 环境变量管理

### 4. 配置环境变量

```bash
touch .env
```
写入：
DB_USER=your_name
DB_PASSWORD=your_passwd
DB_ADMIN_USER=opengauss
DB_ADMIN_PASSWORD=your_admin_password

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
- 门锁模拟器（后台）
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

### 门锁 API（front_door）
| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/locks` | 列出所有门锁状态 |
| GET | `/locks/front_door/state` | 获取门锁当前状态（LOCKED/UNLOCKED、method、actor、battery） |
| GET | `/locks/front_door/events?limit=50` | 获取门锁最近事件 |
| POST | `/locks/front_door/command` | 下发命令，body: `{ "action": "lock|unlock", "method": "PINCODE|APP|FINGERPRINT|REMOTE|KEY", "actor": "Dad", "pin": "1234" }` |

示例：
```bash
# 获取门锁状态
curl http://localhost:5000/locks/front_door/state

# 解锁（PINCODE）
curl -X POST http://localhost:5000/locks/front_door/command \
  -H 'Content-Type: application/json' \
  -d '{"action":"unlock","method":"PINCODE","actor":"Dad","pin":"1234"}'

# 上锁
curl -X POST http://localhost:5000/locks/front_door/command \
  -H 'Content-Type: application/json' \
  -d '{"action":"lock","method":"APP","actor":"Dad"}'
```

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
