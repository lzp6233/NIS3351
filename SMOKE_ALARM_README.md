# 烟雾报警器模块使用说明

## 模块概述

烟雾报警器模块已成功集成到NIS3351智慧家居系统中，提供以下功能：
- 实时监控烟雾浓度（0-100%）
- 自动触发/解除报警
- 电池电量监控
- 测试模式
- 灵敏度调节（low/medium/high）
- 事件历史记录

## 已实现的组件

### 1. 数据库层 (`backend/database.py`)
- `upsert_smoke_alarm_state()` - 更新/插入报警器状态
- `get_smoke_alarm_state(alarm_id)` - 获取单个报警器状态
- `get_all_smoke_alarms()` - 获取所有报警器状态
- `insert_smoke_alarm_event()` - 记录事件
- `get_smoke_alarm_events(alarm_id)` - 获取事件历史

支持 SQLite 和 openGauss 双后端。

### 2. 数据库表 (`init_db.sql`)
**smoke_alarm_state** - 报警器状态表
- alarm_id: 报警器ID（主键）
- location: 位置（living_room/bedroom/kitchen）
- smoke_level: 烟雾浓度（0-100）
- alarm_active: 报警状态
- battery: 电池电量
- test_mode: 测试模式
- sensitivity: 灵敏度（low/medium/high）

**smoke_alarm_events** - 事件表
- id: 事件ID（主键）
- alarm_id: 报警器ID
- event_type: 事件类型
- smoke_level: 触发时的烟雾浓度
- detail: 事件详情
- timestamp: 时间戳

### 3. API路由 (`backend/routes/smoke_alarm.py`)
- `GET /smoke_alarms` - 获取所有报警器
- `GET /smoke_alarms/<alarm_id>` - 获取报警器状态
- `POST /smoke_alarms/<alarm_id>/test` - 启动/停止测试模式
- `POST /smoke_alarms/<alarm_id>/sensitivity` - 更新灵敏度
- `GET /smoke_alarms/<alarm_id>/events` - 获取事件历史
- `POST /smoke_alarms/<alarm_id>/acknowledge` - 确认/清除报警

### 4. MQTT集成 (`backend/mqtt_client.py`)
**订阅的主题:**
- `home/smoke_alarm/+/state` - 报警器状态更新
- `home/smoke_alarm/+/event` - 报警器事件

**消息格式:**
```json
// State message
{
  "location": "living_room",
  "smoke_level": 15.5,
  "alarm_active": false,
  "battery": 95,
  "test_mode": false,
  "sensitivity": "medium"
}

// Event message
{
  "type": "ALARM_TRIGGERED",
  "smoke_level": 65.0,
  "detail": "Smoke level exceeded threshold"
}
```

### 5. 模拟器 (`simulator/smoke_alarm_sim.py`)
模拟3个烟雾报警器：
- smoke_living_room（客厅，中灵敏度）
- smoke_bedroom（卧室，中灵敏度）
- smoke_kitchen（厨房，高灵敏度）

特性：
- 自动生成烟雾浓度（大部分时间低浓度，偶尔高浓度模拟火灾）
- 自动触发/解除报警
- 电池消耗模拟
- 低电量警告
- 支持测试模式

### 6. 前端页面 (`frontend/smoke-alarm.html`)
功能：
- 实时显示所有报警器状态
- 烟雾浓度可视化（进度条）
- 电池电量指示器
- 报警状态动画效果
- 测试模式控制
- 事件历史查看
- 3秒自动刷新

## 快速开始

### 1. 启动系统

```bash
# 方法1：使用启动脚本（需要先修改run.sh添加烟雾报警器模拟器）
sh run.sh

# 方法2：手动启动各个组件
# 终端1：启动Flask服务器
python backend/app.py

# 终端2：启动MQTT客户端（如果独立运行）
python backend/mqtt_client.py

# 终端3：启动烟雾报警器模拟器
python simulator/smoke_alarm_sim.py

# 终端4：启动前端服务器
cd frontend && python -m http.server 8000
```

### 2. 访问前端

打开浏览器访问：
```
http://localhost:8000/smoke-alarm.html
```

### 3. API测试

```bash
# 获取所有报警器
curl http://localhost:5000/smoke_alarms

# 获取特定报警器
curl http://localhost:5000/smoke_alarms/smoke_living_room

# 启动测试模式
curl -X POST http://localhost:5000/smoke_alarms/smoke_living_room/test \
  -H "Content-Type: application/json" \
  -d '{"test_mode": true}'

# 确认报警
curl -X POST http://localhost:5000/smoke_alarms/smoke_living_room/acknowledge

# 获取事件历史
curl http://localhost:5000/smoke_alarms/smoke_living_room/events?limit=10
```

## 修改run.sh添加模拟器

在 `run.sh` 文件中添加以下行：

```bash
# 启动烟雾报警器模拟器
python simulator/smoke_alarm_sim.py &
```

添加位置：在启动门锁模拟器之后，启动前端服务器之前。

## 数据库初始化

如果使用openGauss，运行：
```bash
sh setup_database.sh
```

这会自动创建烟雾报警器的表并初始化3个报警器。

如果使用SQLite（默认），表会在首次运行时自动创建。

## 事件类型

- `INIT` - 初始化
- `ALARM_TRIGGERED` - 报警触发
- `ALARM_CLEARED` - 报警解除
- `TEST_STARTED` - 测试开始
- `TEST_STOPPED` - 测试停止
- `SENSITIVITY_CHANGED` - 灵敏度变更
- `LOW_BATTERY` - 低电量警告
- `ALARM_ACKNOWLEDGED` - 报警已确认

## 灵敏度级别

- `low` - 低灵敏度（阈值×1.2）
- `medium` - 中灵敏度（默认阈值）
- `high` - 高灵敏度（阈值×0.8）

## 报警阈值

- 客厅/卧室：烟雾浓度 ≥ 30% 触发报警
- 厨房：烟雾浓度 ≥ 25% 触发报警（高灵敏度）

## 架构说明

烟雾报警器模块遵循系统的模块化架构：

```
数据流向:
模拟器 → MQTT Broker → mqtt_client.py → database.py → SQLite/openGauss
                            ↓
                     app.py (API)
                            ↓
                   frontend (Web界面)
```

## 扩展建议

1. **添加更多报警器**
   - 在 `simulator/smoke_alarm_sim.py` 的 `SMOKE_ALARMS` 列表中添加
   - 在 `init_db.sql` 中添加初始化数据

2. **集成真实硬件**
   - 修改模拟器发布到实际的硬件主题
   - 硬件按照MQTT消息格式发送数据

3. **添加通知功能**
   - 在报警触发时发送邮件/短信
   - 集成WebSocket实时推送到前端

4. **机器学习集成**
   - 分析历史数据识别异常模式
   - 预测性维护（电池寿命预测）

## 故障排查

### 问题1：模拟器启动后没有数据
- 检查MQTT Broker是否运行：`sudo systemctl status mosquitto`
- 检查mqtt_client.py是否订阅了正确的主题

### 问题2：前端无法获取数据
- 检查Flask服务器是否运行
- 检查浏览器控制台是否有CORS错误
- 确认API端点返回正确的JSON数据

### 问题3：数据库错误
- 如果使用SQLite，检查文件权限
- 如果使用openGauss，确认连接配置正确
- 运行 `sh setup_database.sh` 重新初始化

## 总结

烟雾报警器模块已完全集成到系统中，包括：
- ✅ 数据库表结构和操作函数
- ✅ RESTful API端点
- ✅ MQTT消息处理
- ✅ 设备模拟器
- ✅ 前端Web界面

所有组件都遵循系统的现有架构模式，可以无缝集成到现有系统中。
