# NIS3351 项目设置指南

## 📌 新开发者快速上手

欢迎加入 NIS3351 智慧家居系统项目！这份文档将帮助你快速搭建开发环境。

---

## ✅ 检查清单

在开始之前，确保你的系统满足以下要求：

- [ ] Python 3.8+ 已安装
- [ ] openGauss 数据库已安装并运行
- [ ] MQTT Broker (Mosquitto) 已安装并运行
- [ ] Git 已安装

---

## 🚀 5分钟快速开始

### 步骤 1：克隆项目

```bash
git clone <项目地址>
cd NIS3351
```

### 步骤 2：配置数据库连接

创建 `.env` 文件：

```bash
cat > .env << 'EOF'
# 数据库配置
DB_HOST=127.0.0.1
DB_PORT=7654
DB_NAME=nis3351
DB_ADMIN_USER=opengauss
DB_ADMIN_PASSWORD=请替换为你的管理员密码
DB_USER=nis3351_user
DB_PASSWORD=请替换为你的用户密码

# MQTT 配置
MQTT_BROKER=localhost
MQTT_PORT=1883
EOF
```

然后编辑并替换密码：

```bash
vi .env
```

### 步骤 3：一键初始化

运行初始化脚本：

```bash
sh setup_database.sh
```

这个脚本会自动：
- ✅ 创建 Python 虚拟环境
- ✅ 安装所有依赖包
- ✅ 创建数据库和表
- ✅ 初始化测试数据（空调、门锁）

### 步骤 4：启动系统

```bash
sh run.sh
```

### 步骤 5：访问系统

打开浏览器访问：
- **主页**：http://localhost:8000
- **空调控制**：http://localhost:8000/air-conditioner.html
- **门锁控制**：http://localhost:8000/door-lock.html

---

## 📋 详细说明

### 项目结构

```
NIS3351/
├── backend/              # 后端代码
│   ├── app.py           # Flask 主应用
│   ├── config.py        # 配置管理
│   ├── database.py      # 数据库操作
│   ├── mqtt_client.py   # MQTT 客户端
│   └── routes/          # 模块化路由
│       ├── air_conditioner.py  # 空调模块（你负责的）
│       └── lock.py             # 门锁模块
├── frontend/            # 前端页面
├── simulator/           # 设备模拟器
│   ├── sensor_sim.py   # 温湿度传感器（会根据空调状态调整温度）
│   └── lock_sim.py     # 门锁模拟器
├── init_db.sql         # 数据库初始化 SQL
├── init_ac.py          # 空调数据初始化
├── setup_database.sh   # 数据库一键初始化脚本
├── run.sh              # 系统启动脚本
└── readme.md           # 完整文档
```

### 你负责的模块：空调控制

#### 文件位置
- 后端 API：`backend/routes/air_conditioner.py`
- 前端页面：`frontend/air-conditioner.html`
- 前端逻辑：`frontend/air-conditioner.js`
- 数据库函数：`backend/database.py` (搜索 `ac_` 相关函数)
- 模拟器：`simulator/sensor_sim.py` (温度会根据空调设置动态调整)

#### 主要功能
1. **查看空调状态**：显示当前温度、目标温度、开关状态
2. **控制空调**：开关空调、设置目标温度（18-30°C）
3. **智能温控**：传感器模拟器会根据空调设置动态调整温度
4. **事件记录**：记录所有操作历史

#### API 接口
- `GET /ac` - 获取所有空调
- `GET /ac/<ac_id>` - 获取空调状态
- `POST /ac/<ac_id>/control` - 控制空调
- `GET /ac/<ac_id>/events` - 查看操作历史

---

## 🔧 开发时常用命令

### 启动系统
```bash
sh run.sh
```

### 停止系统
```bash
pkill -f 'python.*backend|python.*simulator|http.server'
```

### 重置数据库
```bash
sh setup_database.sh
```

### 重新初始化空调数据
```bash
source venv/bin/activate
python init_ac.py
```

### 查看日志
```bash
# 后端日志在终端中实时显示
# 或者查看 run.sh 启动的进程输出
```

---

## 🐛 常见问题

### 1. 数据库连接失败

**错误信息**：`could not connect to database`

**解决方法**：
```bash
# 检查 openGauss 是否运行
ps -ef | grep gaussdb

# 检查 .env 文件配置是否正确
cat .env
```

### 2. MQTT 连接失败

**错误信息**：`Connection refused on port 1883`

**解决方法**：
```bash
# 启动 Mosquitto
sudo systemctl start mosquitto

# 检查状态
sudo systemctl status mosquitto
```

### 3. 前端无法访问后端

**错误信息**：CORS error 或 404

**解决方法**：
1. 清除浏览器缓存（Ctrl+Shift+Delete）
2. 使用硬刷新（Ctrl+Shift+R）
3. 重启后端服务

### 4. 空调控制不生效

**问题**：点击按钮后温度没有变化

**检查项**：
1. 确认空调数据已初始化：`python init_ac.py`
2. 确认传感器模拟器正在运行
3. 查看浏览器控制台是否有错误

---

## 📞 获取帮助

如果遇到问题：

1. **查看完整文档**：`cat readme.md`
2. **查看配置说明**：`cat CONFIG_TEMPLATE.md`
3. **联系项目组其他成员**

---

## 🎯 开发提示

### 修改代码后

1. **后端代码修改**：需要重启 Flask 服务
   ```bash
   pkill -f 'python.*backend'
   sh run.sh
   ```

2. **前端代码修改**：直接刷新浏览器即可

3. **数据库结构修改**：
   - 更新 `init_db.sql`
   - 更新 `backend/database.py` 中相应的函数
   - 运行 `sh setup_database.sh`

### 测试你的修改

1. **测试 API**：
   ```bash
   # 获取空调状态
   curl http://localhost:5000/ac/ac_room1
   
   # 控制空调
   curl -X POST http://localhost:5000/ac/ac_room1/control \
     -H "Content-Type: application/json" \
     -d '{"power": true, "target_temp": 26}'
   ```

2. **测试前端**：
   - 打开浏览器开发者工具（F12）
   - 查看 Network 标签查看请求
   - 查看 Console 标签查看错误

### 代码提交前

- [ ] 确保系统能正常启动
- [ ] 测试你负责的模块所有功能
- [ ] 检查是否有 Python 语法错误
- [ ] 更新文档（如果有 API 变更）

---

祝开发顺利！🎉

