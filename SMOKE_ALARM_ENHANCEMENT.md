# 烟雾报警器模块增强方案

## 功能概述

为烟雾报警器模块添加以下增强功能：

### 1. 房间管理系统 (Rooms Management)
- 创建统一的房间表，关联所有智能设备
- 实现跨设备联动（烟雾报警触发时自动控制其他设备）

### 2. 自动化响应规则 (Automation Rules)
- 定义烟雾报警触发时的自动化操作
- 例如：报警时自动解锁门锁、关闭空调、开启排气扇、打开灯光照明逃生路线

### 3. 用户通知系统 (User Notifications)
- 存储用户联系方式和通知偏好
- 支持多种通知渠道（邮件、短信、App推送）
- 记录通知发送历史

### 4. 设备维护管理 (Device Maintenance)
- 记录设备维护历史（电池更换、清洁、测试）
- 自动提醒维护时间
- 设备生命周期管理

### 5. 报警确认系统 (Alarm Acknowledgment)
- 记录谁在何时确认了报警
- 追踪响应时间和处理结果
- 支持添加处理备注

### 6. 统计分析功能 (Statistics & Analytics)
- 报警频率统计
- 误报率分析
- 设备健康度评估
- 生成可视化报表

## 数据库表设计

### 新增表

#### 1. rooms (房间表) - 核心关联表
```sql
CREATE TABLE rooms (
    room_id VARCHAR(50) PRIMARY KEY,
    room_name VARCHAR(100) NOT NULL,
    floor INTEGER,
    area FLOAT,  -- 面积（平方米）
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. smoke_alarm_response_rules (报警响应规则表)
```sql
CREATE TABLE smoke_alarm_response_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    alarm_id VARCHAR(50) REFERENCES smoke_alarm_state(alarm_id),
    room_id VARCHAR(50) REFERENCES rooms(room_id),
    trigger_condition VARCHAR(50),  -- smoke_level_threshold, alarm_triggered
    condition_value FLOAT,  -- 触发条件的值
    action_type VARCHAR(50),  -- unlock_door, turn_off_ac, turn_on_lights, send_notification
    action_target VARCHAR(100),  -- 目标设备ID
    action_params TEXT,  -- JSON格式的操作参数
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. user_notification_config (用户通知配置表)
```sql
CREATE TABLE user_notification_config (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    username VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    notify_on_alarm BOOLEAN DEFAULT true,
    notify_on_low_battery BOOLEAN DEFAULT true,
    notify_on_maintenance_due BOOLEAN DEFAULT true,
    notification_channels TEXT,  -- JSON: ["email", "sms", "push"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. notification_history (通知历史表)
```sql
CREATE TABLE notification_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    alarm_id VARCHAR(50),
    notification_type VARCHAR(50),  -- alarm, low_battery, maintenance
    channel VARCHAR(20),  -- email, sms, push
    subject VARCHAR(255),
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'sent',  -- sent, failed, pending
    error_message TEXT
);
```

#### 5. device_maintenance (设备维护记录表)
```sql
CREATE TABLE device_maintenance (
    id SERIAL PRIMARY KEY,
    alarm_id VARCHAR(50) REFERENCES smoke_alarm_state(alarm_id),
    maintenance_type VARCHAR(50),  -- battery_replacement, cleaning, test, inspection
    performed_by VARCHAR(100),
    maintenance_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_maintenance_date TIMESTAMP,
    notes TEXT,
    cost DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 6. alarm_acknowledgments (报警确认记录表)
```sql
CREATE TABLE alarm_acknowledgments (
    id SERIAL PRIMARY KEY,
    alarm_id VARCHAR(50) NOT NULL,
    event_id INTEGER REFERENCES smoke_alarm_events(id),
    acknowledged_by VARCHAR(100) NOT NULL,
    acknowledged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time INTEGER,  -- 响应时间（秒）
    action_taken TEXT,  -- 采取的行动
    resolution VARCHAR(50),  -- false_alarm, real_fire, resolved
    notes TEXT
);
```

#### 7. alarm_statistics (报警统计缓存表)
```sql
CREATE TABLE alarm_statistics (
    id SERIAL PRIMARY KEY,
    alarm_id VARCHAR(50),
    room_id VARCHAR(50),
    stat_date DATE,
    total_alarms INTEGER DEFAULT 0,
    false_alarms INTEGER DEFAULT 0,
    real_alarms INTEGER DEFAULT 0,
    avg_response_time INTEGER,  -- 平均响应时间（秒）
    max_smoke_level FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(alarm_id, stat_date)
);
```

### 修改现有表

#### smoke_alarm_state 添加字段
```sql
ALTER TABLE smoke_alarm_state ADD COLUMN room_id VARCHAR(50) REFERENCES rooms(room_id);
ALTER TABLE smoke_alarm_state ADD COLUMN installation_date TIMESTAMP;
ALTER TABLE smoke_alarm_state ADD COLUMN last_maintenance_date TIMESTAMP;
ALTER TABLE smoke_alarm_state ADD COLUMN device_model VARCHAR(100);
ALTER TABLE smoke_alarm_state ADD COLUMN firmware_version VARCHAR(50);
```

#### 其他设备表也关联到rooms
```sql
ALTER TABLE ac_state ADD COLUMN room_id VARCHAR(50) REFERENCES rooms(room_id);
ALTER TABLE lock_state ADD COLUMN room_id VARCHAR(50) REFERENCES rooms(room_id);
ALTER TABLE lighting_state ADD COLUMN room_id VARCHAR(50) REFERENCES rooms(room_id);
```

## API端点设计

### 房间管理
- `GET /rooms` - 获取所有房间
- `GET /rooms/<room_id>` - 获取房间详情及所有设备
- `POST /rooms` - 创建房间
- `PUT /rooms/<room_id>` - 更新房间信息
- `DELETE /rooms/<room_id>` - 删除房间

### 自动化规则
- `GET /smoke_alarms/rules` - 获取所有响应规则
- `POST /smoke_alarms/rules` - 创建响应规则
- `PUT /smoke_alarms/rules/<rule_id>` - 更新规则
- `DELETE /smoke_alarms/rules/<rule_id>` - 删除规则
- `POST /smoke_alarms/rules/<rule_id>/test` - 测试规则

### 通知管理
- `GET /notifications/config` - 获取通知配置
- `PUT /notifications/config` - 更新通知配置
- `GET /notifications/history` - 获取通知历史
- `POST /notifications/test` - 发送测试通知

### 设备维护
- `GET /smoke_alarms/<alarm_id>/maintenance` - 获取维护记录
- `POST /smoke_alarms/<alarm_id>/maintenance` - 添加维护记录
- `GET /smoke_alarms/maintenance/due` - 获取需要维护的设备

### 报警确认
- `POST /smoke_alarms/<alarm_id>/acknowledge` - 确认报警（增强版）
- `GET /smoke_alarms/<alarm_id>/acknowledgments` - 获取确认历史

### 统计分析
- `GET /smoke_alarms/statistics` - 获取总体统计
- `GET /smoke_alarms/<alarm_id>/statistics` - 获取单个设备统计
- `GET /smoke_alarms/statistics/report` - 生成报表

## 前端页面设计

### 1. alarm-dashboard.html (报警监控仪表板)
- 实时显示所有报警器状态
- 地图/平面图展示
- 实时报警通知
- 快速响应按钮

### 2. alarm-statistics.html (统计分析页面)
- 报警趋势图表
- 房间对比分析
- 误报率统计
- 设备健康度评分

### 3. device-maintenance.html (设备维护管理页面)
- 维护记录列表
- 维护提醒日历
- 添加维护记录表单
- 维护成本统计

### 4. automation-rules.html (自动化规则配置页面)
- 规则列表和编辑器
- 可视化规则配置器
- 规则测试工具
- 规则执行日志

### 5. notification-settings.html (通知设置页面)
- 用户联系方式配置
- 通知渠道选择
- 通知历史查看
- 测试通知功能

### 6. room-management.html (房间管理页面)
- 房间列表
- 设备关联视图
- 房间平面图编辑
- 批量设备配置

## 实现优先级

### Phase 1 (核心功能)
1. 房间表和关联关系
2. 自动化响应规则基础
3. 报警确认系统

### Phase 2 (增强功能)
1. 用户通知系统
2. 设备维护管理
3. 基础统计功能

### Phase 3 (高级功能)
1. 高级统计分析
2. 可视化仪表板
3. 报表生成

## 技术亮点

1. **跨设备联动** - 通过房间关联实现设备协同
2. **规则引擎** - 灵活的自动化响应规则系统
3. **实时通知** - 多渠道通知支持
4. **数据分析** - 完整的统计分析和可视化
5. **外键约束** - 保证数据完整性
6. **可扩展性** - 易于添加新设备类型和规则
