# NIS3351 智慧家居系统

一个基于 Flask + MQTT + openGauss 的智慧家居监控系统，支持温湿度监控、空调控制、全屋灯具控制和智能门锁管理。

## 📋 功能模块

- **温湿度监控**：实时监控各房间的温度和湿度数据
- **空调控制**：远程控制空调开关和目标温度，模拟器会根据设置智能调节温度
- **全屋灯具控制**：关闭“智能调节”模式时，远程控制各房间的灯具开关；开启“智能调节”模式时，各房间灯具亮度将根据所处房间亮度调整
- **智能门锁**：门锁状态监控和远程控制

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



## 🏗️ 系统架构

```
NIS3351/
├── backend/           # Flask 后端
│   ├── app.py        # 主应用
│   ├── config.py     # 配置文件
│   ├── database.py   # 数据库操作
│   ├── mqtt_client.py # MQTT 客户端
│   └── routes/       # 模块化路由
│       ├── air_conditioner.py  # 空调模块
│       └── lock.py            # 门锁模块
├── frontend/         # 前端页面
│   ├── index.html    # 主页
│   ├── air-conditioner.html  # 空调控制页
│   └── lock.html     # 门锁控制页
├── simulator/        # 设备模拟器
│   ├── sensor_sim.py # 温湿度传感器模拟器（智能感知空调）
│   └── lock_sim.py   # 门锁模拟器
├── init_db.sql       # 数据库初始化 SQL
├── init_ac.py        # 空调数据初始化脚本
├── setup_database.sh # 数据库一键初始化脚本
└── run.sh           # 系统启动脚本
```

**数据流向**：
```
传感器模拟器/门锁模拟器 → MQTT Broker → MQTT 客户端 → openGauss 数据库
         ↑                                    ↓
         |                            Flask Web 服务器
         |                                    ↓
         |                            前端界面（ECharts）
         |                                    ↓
         └──────────── 空调控制反馈 ──────────┘
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

创建 `.env` 文件（参考 `CONFIG_TEMPLATE.md`）：

```bash
# 复制配置模板
cat > .env << 'EOF'
# 数据库配置
DB_HOST=127.0.0.1
DB_PORT=7654
DB_NAME=smart_name
DB_ADMIN_USER=opengauss
DB_ADMIN_PASSWORD=your_admin_password_here
DB_USER=nis3351_user
DB_PASSWORD=your_user_password_here

# MQTT 配置
MQTT_BROKER=localhost
MQTT_PORT=1883
EOF

# 编辑配置文件，替换密码
vi .env
```

**配置说明**：
- `DB_HOST`: openGauss 数据库主机地址
- `DB_PORT`: openGauss 端口（默认 7654）
- `DB_ADMIN_USER`: 管理员用户（通常是 `opengauss`）
- `DB_USER`: 应用用户名（建议 `nis3351_user`）
- 详细配置说明请查看 `CONFIG_TEMPLATE.md`

### 5. 一键初始化数据库

运行初始化脚本，自动完成数据库创建、表创建、权限配置和数据初始化：

```bash
# 给脚本添加执行权限（首次运行）
chmod +x setup_database.sh

# 运行初始化脚本
sh setup_database.sh
```

**初始化脚本会自动完成以下步骤**：
1. ✅ 测试数据库连接
2. ✅ 创建数据库和所有表：
   - `temperature_humidity_data` - 温湿度数据
   - `lock_state` - 门锁状态
   - `lock_events` - 门锁事件
   - `ac_state` - 空调状态
   - `ac_events` - 空调事件
3. ✅ 配置用户权限
4. ✅ 初始化应用数据：
   - 空调：`ac_room1`, `ac_room2`
   - 门锁：`FRONT_DOOR`

如果初始化失败，请检查：
- openGauss 是否正在运行：`ps -ef | grep gaussdb`
- `.env` 文件中的配置是否正确
- 网络端口是否开放

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

### 温湿度模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/` | API 信息 |
| GET | `/devices` | 获取所有设备列表 |
| GET | `/history/<device_id>?limit=50` | 获取指定设备历史数据 |
| GET | `/latest/<device_id>` | 获取指定设备最新数据 |

### 空调模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/ac` | 获取所有空调列表 |
| GET | `/ac/<ac_id>` | 获取空调状态 |
| POST | `/ac/<ac_id>/control` | 控制空调 |
| GET | `/ac/<ac_id>/events` | 获取空调事件历史 |

**控制空调示例**：
```bash
curl -X POST http://localhost:5000/ac/ac_room1/control \
  -H "Content-Type: application/json" \
  -d '{
    "power": true,
    "target_temp": 26.0,
    "mode": "cool",
    "fan_speed": "auto"
  }'
```

### 门锁模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/lock` | 获取所有门锁列表 |
| GET | `/lock/<lock_id>` | 获取门锁状态 |
| POST | `/lock/<lock_id>/control` | 控制门锁 |
| GET | `/lock/<lock_id>/events` | 获取门锁事件历史 |

**控制门锁示例**：
```bash
curl -X POST http://localhost:5000/lock/FRONT_DOOR/control \
  -H "Content-Type: application/json" \
  -d '{
    "action": "lock",
    "method": "remote",
    "actor": "用户A"
  }'
```

### 烟雾报警器模块

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/smoke_alarms` | 获取所有烟雾报警器列表 |
| GET | `/smoke_alarms/<alarm_id>` | 获取烟雾报警器状态 |
| POST | `/smoke_alarms/<alarm_id>/test` | 启动/停止测试模式 |
| POST | `/smoke_alarms/<alarm_id>/sensitivity` | 更新灵敏度设置 |
| GET | `/smoke_alarms/<alarm_id>/events` | 获取事件历史 |
| POST | `/smoke_alarms/<alarm_id>/acknowledge` | 确认/清除报警 |

**启动测试模式示例**：
```bash
curl -X POST http://localhost:5000/smoke_alarms/smoke_living_room/test \
  -H "Content-Type: application/json" \
  -d '{
    "test_mode": true
  }'
```

**更新灵敏度示例**：
```bash
curl -X POST http://localhost:5000/smoke_alarms/smoke_kitchen/sensitivity \
  -H "Content-Type: application/json" \
  -d '{
    "sensitivity": "high"
  }'
```

**确认报警示例**：
```bash
curl -X POST http://localhost:5000/smoke_alarms/smoke_bedroom/acknowledge \
  -H "Content-Type: application/json"
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

### smoke_alarm_state

| 字段 | 类型 | 说明 |
|------|------|------|
| alarm_id | VARCHAR(50) | 报警器ID（主键） |
| location | VARCHAR(50) | 位置（living_room/bedroom/kitchen） |
| smoke_level | FLOAT | 烟雾浓度（0-100） |
| alarm_active | BOOLEAN | 报警状态 |
| battery | INTEGER | 电池电量（0-100） |
| test_mode | BOOLEAN | 测试模式 |
| sensitivity | VARCHAR(20) | 灵敏度（low/medium/high） |
| updated_at | TIMESTAMP | 最后更新时间 |

### smoke_alarm_events

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键，自增 |
| alarm_id | VARCHAR(50) | 报警器ID |
| event_type | VARCHAR(32) | 事件类型 |
| smoke_level | FLOAT | 触发时烟雾浓度 |
| detail | TEXT | 事件详情 |
| timestamp | TIMESTAMP | 事件时间 |

---

## 🎯 开发者指南

### 模块化架构

后端采用 Flask Blueprint 进行模块化开发，每个功能模块独立管理：

- **空调模块**：`backend/routes/air_conditioner.py`
- **门锁模块**：`backend/routes/lock.py`
- **烟雾报警器模块**：`backend/routes/smoke_alarm.py`

这种设计便于：
- ✅ 多人协作开发，互不干扰
- ✅ 代码组织清晰，易于维护
- ✅ 功能模块独立，便于测试

### 添加新设备模块

如需添加新的设备类型（如窗帘、灯光等）：

1. **在 `backend/routes/` 创建新模块**：
   ```python
   # backend/routes/curtain.py
   from flask import Blueprint, request, jsonify
   
   curtain_bp = Blueprint('curtain', __name__)
   
   @curtain_bp.route('/curtain/<curtain_id>', methods=['GET'])
   def get_curtain_status(curtain_id):
       # 实现逻辑
       return jsonify({"status": "success"})
   ```

2. **在 `backend/app.py` 注册 Blueprint**：
   ```python
   from routes.curtain import curtain_bp
   app.register_blueprint(curtain_bp)
   ```

3. **在 `backend/database.py` 添加数据库函数**：
   ```python
   def get_curtain_state(curtain_id):
       # 实现数据库查询
       pass
   ```

4. **更新 `init_db.sql` 添加表结构**

5. **运行数据库迁移**：
   ```bash
   sh setup_database.sh
   ```

### 数据库操作规范

所有数据库操作统一在 `backend/database.py` 中管理，自动兼容 openGauss 和 SQLite：

```python
from database import get_ac_state, upsert_ac_state

# 获取数据
state = get_ac_state('ac_room1')

# 更新数据
upsert_ac_state(
    ac_id='ac_room1',
    device_id='room1',
    power=True,
    target_temp=26.0
)
```

### 配置管理

所有配置统一在 `backend/config.py` 中管理：

```python
# 添加新配置
NEW_SETTING = os.getenv('NEW_SETTING', 'default_value')
```

然后在 `.env` 文件中设置：
```bash
NEW_SETTING=your_value
```

### 开发规范

1. **代码提交前**：确保所有模块正常运行
2. **数据库修改**：同步更新 `init_db.sql` 和 `database.py`
3. **新增配置**：添加到 `CONFIG_TEMPLATE.md` 中并说明
4. **API 修改**：更新本 README 中的 API 接口文档

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
