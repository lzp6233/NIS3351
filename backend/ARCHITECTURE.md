# 后端架构说明

## 📂 目录结构

```
backend/
├── devices/                    # 设备功能模块（新增）
│   ├── __init__.py            # 模块初始化，统一导出
│   ├── sensor.py              # 温湿度传感器功能
│   └── air_conditioner.py     # 空调功能
├── app.py                     # Flask Web 服务器
├── database.py                # 数据库基础层（连接管理）
├── mqtt_client.py             # MQTT 客户端
└── config.py                  # 配置管理
```

---

## 🔧 模块化设计

### 1. **devices/sensor.py** - 温湿度传感器模块

**功能：**
- `insert_sensor_data(data, device_id)` - 插入传感器数据
- `get_recent_data(device_id, limit)` - 查询历史数据
- `get_devices()` - 获取所有设备列表
- `get_latest_data(device_id)` - 获取最新数据

**用途：** 管理多个房间的温湿度传感器数据

---

### 2. **devices/air_conditioner.py** - 空调模块（预留）

**功能：**
- `upsert_ac_state(ac_id, power, mode, temperature, fan_speed, ts)` - 更新空调状态
- `insert_ac_event(ac_id, event_type, detail, ts)` - 记录空调操作
- `get_ac_state(ac_id)` - 获取空调当前状态
- `get_all_acs()` - 获取所有空调状态
- `get_ac_events(ac_id, limit)` - 获取空调操作历史

**用途：** 为未来的空调控制功能预留接口

**支持的模式：**
- COOL - 制冷
- HEAT - 制热
- FAN - 送风
- DRY - 除湿
- AUTO - 自动

---

## 🎯 设计优势

### 1. **单一职责原则**
- 每个设备功能独立为一个模块
- 模块职责清晰，易于理解和维护

### 2. **解耦合**
- 设备功能与数据库连接分离
- app.py 只需要导入需要的设备模块
- 便于单独测试各个模块

### 3. **易于扩展**
- 新增设备类型只需在 `devices/` 下创建新文件
- 不影响现有代码
- 遵循开放封闭原则

### 4. **代码复用**
- `database.py` 提供统一的 `get_connection()`
- 所有设备模块都使用相同的连接逻辑
- 支持 SQLite 和 openGauss 双数据库

---

## 📝 使用示例

### 在 app.py 中使用

```python
# 导入传感器功能
from devices.sensor import get_recent_data, get_devices

# 导入门锁功能
from devices.lock import get_lock_state, upsert_lock_state

# 使用
@app.route("/devices")
def devices():
    return jsonify(get_devices())

@app.route("/locks/<lock_id>/state")
def lock_state(lock_id):
    return jsonify(get_lock_state(lock_id))
```

### 在 mqtt_client.py 中使用

```python
from devices.sensor import insert_sensor_data
from devices.lock import insert_lock_event

# 接收传感器数据
def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    insert_sensor_data(data, device_id="room1")
```

---

## 🔄 数据流向

```
传感器/设备 → MQTT Broker → mqtt_client.py → devices/*.py → database
                                                        ↑
前端请求     → app.py        → devices/*.py ← ← ← ← ← ←┘
```

---

## 🚀 未来扩展

可以轻松添加新的设备类型：

```
devices/
├── curtain.py          # 智能窗帘
├── camera.py           # 监控摄像头
├── light.py            # 智能灯光
└── socket.py           # 智能插座
```

只需：
1. 创建新的 `.py` 文件
2. 实现设备的 CRUD 操作
3. 在 `__init__.py` 中导出
4. 在 `app.py` 和 `mqtt_client.py` 中使用

---

## ⚙️ 配置说明

所有设备模块都从 `config.py` 读取配置：
- `DB_TYPE` - 数据库类型（sqlite/opengauss）
- `DB_CONFIG` - openGauss 连接配置
- `DB_PATH` - SQLite 数据库文件路径

自动适配不同的数据库，无需修改业务代码。

