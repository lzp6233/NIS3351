-- ============================================
-- NIS3351 智能家居监控系统数据库初始化脚本
-- 使用方法：gsql -d smart_home -h 127.0.0.1 -p 7654 -U lzp -W password -f init_db.sql
-- ============================================

-- 注意：数据库 smart_home 应该已经存在
-- 如果需要创建数据库，请使用管理员账户执行：CREATE DATABASE smart_home;

-- 1. 创建温湿度传感器数据表
SELECT 'Creating table: temperature_humidity_data...' AS status;

CREATE TABLE IF NOT EXISTS temperature_humidity_data (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) DEFAULT 'room1',
    temperature FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 创建索引
SELECT 'Creating indexes...' AS status;

CREATE INDEX IF NOT EXISTS idx_temp_hum_timestamp 
ON temperature_humidity_data(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_temp_hum_device 
ON temperature_humidity_data(device_id);

-- 5. 插入测试数据
SELECT 'Inserting test data...' AS status;

INSERT INTO temperature_humidity_data (device_id, temperature, humidity) VALUES 
    ('room1', 25.5, 55.0),
    ('room1', 26.0, 52.3),
    ('room1', 24.8, 58.1),
    ('room2', 23.5, 60.0),
    ('room2', 24.0, 58.5);

-- 6. 显示表结构
SELECT 'Table structure:' AS status;
\d temperature_humidity_data

-- 7. 显示数据统计
SELECT 'Data statistics:' AS status;
SELECT 
    device_id,
    COUNT(*) as data_count,
    ROUND(AVG(temperature)::numeric, 2) as avg_temp,
    ROUND(AVG(humidity)::numeric, 2) as avg_humidity
FROM temperature_humidity_data
GROUP BY device_id;

-- 8. 显示最近的数据
SELECT 'Recent data:' AS status;
SELECT * FROM temperature_humidity_data 
ORDER BY timestamp DESC 
LIMIT 10;

-- 9. 智慧门锁：单把大门锁的表结构
SELECT 'Creating tables for smart lock...' AS status;

-- 当前锁状态表
CREATE TABLE IF NOT EXISTS lock_state (
    lock_id VARCHAR(50) PRIMARY KEY,
    locked BOOLEAN NOT NULL,
    method VARCHAR(20),                 -- 开锁方式：PINCODE/FINGERPRINT/FACE
    actor VARCHAR(64),                 
    battery INTEGER DEFAULT 100,        -- 电量百分比
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 锁事件流水表（审计）
CREATE TABLE IF NOT EXISTS lock_events (
    id SERIAL PRIMARY KEY,
    lock_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(32) NOT NULL,    -- lock/unlock/unlock_success/unlock_fail/tamper/etc
    method VARCHAR(20),                 -- 使用方式
    actor VARCHAR(64),                  -- 操作人
    detail TEXT,                        -- 其他信息
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lock_events_lock_time
ON lock_events(lock_id, timestamp DESC);

-- 初始化一把大门锁的状态（仅在不存在时插入）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM lock_state WHERE lock_id = 'FRONT_DOOR') THEN
        INSERT INTO lock_state (lock_id, locked, method, actor, battery)
        VALUES ('FRONT_DOOR', TRUE, NULL, NULL, 100);
    END IF;
END $$;

-- 插入示例事件
INSERT INTO lock_events (lock_id, event_type, method, actor, detail)
VALUES ('FRONT_DOOR', 'INIT', NULL, NULL, 'Initialized with LOCKED=TRUE');

-- 门锁用户认证表
CREATE TABLE IF NOT EXISTS lock_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    face_image_path VARCHAR(255),
    fingerprint_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 自动锁定配置表
CREATE TABLE IF NOT EXISTS lock_auto_config (
    lock_id VARCHAR(50) PRIMARY KEY,
    auto_lock_enabled BOOLEAN DEFAULT true,
    auto_lock_delay INTEGER DEFAULT 5,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. 空调控制：智能空调表结构
SELECT 'Creating tables for air conditioner...' AS status;

-- 空调状态表
CREATE TABLE IF NOT EXISTS ac_state (
    ac_id VARCHAR(50) PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    power BOOLEAN DEFAULT false,
    mode VARCHAR(20) DEFAULT 'cool',        -- cool/heat/fan/dehumidify
    target_temp FLOAT DEFAULT 26.0,
    current_temp FLOAT,
    current_humidity FLOAT,
    fan_speed VARCHAR(20) DEFAULT 'auto',   -- auto/low/medium/high
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 空调事件表（操作历史）
CREATE TABLE IF NOT EXISTS ac_events (
    id SERIAL PRIMARY KEY,
    ac_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(32) NOT NULL,        -- power_on/power_off/temp_change/mode_change
    old_value TEXT,
    new_value TEXT,
    detail TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ac_events_ac_time
ON ac_events(ac_id, timestamp DESC);

-- 初始化空调状态（统一房间命名）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ac_state WHERE ac_id = 'ac_living') THEN
        INSERT INTO ac_state (ac_id, device_id, power, mode, target_temp, fan_speed)
        VALUES ('ac_living', 'living', false, 'cool', 26.0, 'auto');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM ac_state WHERE ac_id = 'ac_bedroom1') THEN
        INSERT INTO ac_state (ac_id, device_id, power, mode, target_temp, fan_speed)
        VALUES ('ac_bedroom1', 'bedroom1', false, 'cool', 26.0, 'auto');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM ac_state WHERE ac_id = 'ac_bedroom2') THEN
        INSERT INTO ac_state (ac_id, device_id, power, mode, target_temp, fan_speed)
        VALUES ('ac_bedroom2', 'bedroom2', false, 'cool', 26.0, 'auto');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM ac_state WHERE ac_id = 'ac_kitchen') THEN
        INSERT INTO ac_state (ac_id, device_id, power, mode, target_temp, fan_speed)
        VALUES ('ac_kitchen', 'kitchen', false, 'cool', 26.0, 'auto');
    END IF;
END $$;

-- 插入初始化事件
INSERT INTO ac_events (ac_id, event_type, detail)
VALUES
    ('ac_living', 'INIT', 'Air conditioner initialized'),
    ('ac_bedroom1', 'INIT', 'Air conditioner initialized'),
    ('ac_bedroom2', 'INIT', 'Air conditioner initialized'),
    ('ac_kitchen', 'INIT', 'Air conditioner initialized');

-- 全屋灯具控制：智能灯具表结构
SELECT 'Creating tables for smart lighting...' AS status;

-- 灯具状态表
CREATE TABLE IF NOT EXISTS lighting_state (
    light_id VARCHAR(50) PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    power BOOLEAN DEFAULT false,
    brightness INTEGER DEFAULT 50,           -- 亮度百分比 0-100
    auto_mode BOOLEAN DEFAULT false,         -- 智能调节模式
    room_brightness FLOAT,                   -- 房间亮度传感器读数
    color_temp INTEGER DEFAULT 4000,         -- 色温 (K)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 灯具事件表（操作历史）
CREATE TABLE IF NOT EXISTS lighting_events (
    id SERIAL PRIMARY KEY,
    light_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(32) NOT NULL,          -- power_on/power_off/brightness_change/auto_mode_change
    old_value TEXT,
    new_value TEXT,
    detail TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. 房间管理：统一的房间表（作为核心关联表）
SELECT 'Creating rooms table...' AS status;

CREATE TABLE IF NOT EXISTS rooms (
    room_id VARCHAR(50) PRIMARY KEY,
    room_name VARCHAR(100) NOT NULL,
    floor INTEGER DEFAULT 1,
    area FLOAT,                                 -- 面积（平方米）
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化房间数据（统一命名：living, bedroom1, bedroom2, kitchen）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM rooms WHERE room_id = 'living') THEN
        INSERT INTO rooms (room_id, room_name, floor, area, description)
        VALUES ('living', '客厅', 1, 35.5, '主要活动区域');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM rooms WHERE room_id = 'bedroom1') THEN
        INSERT INTO rooms (room_id, room_name, floor, area, description)
        VALUES ('bedroom1', '主卧', 1, 20.0, '主卧室');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM rooms WHERE room_id = 'bedroom2') THEN
        INSERT INTO rooms (room_id, room_name, floor, area, description)
        VALUES ('bedroom2', '次卧', 1, 15.0, '次卧室');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM rooms WHERE room_id = 'kitchen') THEN
        INSERT INTO rooms (room_id, room_name, floor, area, description)
        VALUES ('kitchen', '厨房', 1, 12.0, '烹饪区域');
    END IF;
END $$;

-- 12. 烟雾报警器：智能烟雾报警器表结构（增强版）
SELECT 'Creating tables for smoke alarm...' AS status;

-- 烟雾报警器状态表（增强版）
CREATE TABLE IF NOT EXISTS smoke_alarm_state (
    alarm_id VARCHAR(50) PRIMARY KEY,
    room_id VARCHAR(50) REFERENCES rooms(room_id),  -- 关联到房间表
    location VARCHAR(50) NOT NULL,              -- 位置：living_room/bedroom/kitchen等
    smoke_level FLOAT DEFAULT 0.0,              -- 烟雾浓度 (0-100)
    alarm_active BOOLEAN DEFAULT false,         -- 报警状态
    battery INTEGER DEFAULT 100,                -- 电池电量百分比
    test_mode BOOLEAN DEFAULT false,            -- 测试模式
    sensitivity VARCHAR(20) DEFAULT 'medium',   -- 灵敏度：low/medium/high
    installation_date TIMESTAMP,                -- 安装日期
    last_maintenance_date TIMESTAMP,            -- 最后维护日期
    device_model VARCHAR(100) DEFAULT 'SA-2024',-- 设备型号
    firmware_version VARCHAR(50) DEFAULT '1.0.0',-- 固件版本
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 烟雾报警器事件表
CREATE TABLE IF NOT EXISTS smoke_alarm_events (
    id SERIAL PRIMARY KEY,
    alarm_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(32) NOT NULL,            -- ALARM_TRIGGERED/ALARM_CLEARED/TEST_STARTED/LOW_BATTERY等
    smoke_level FLOAT,                          -- 触发时的烟雾浓度
    detail TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 自动化响应规则表
CREATE TABLE IF NOT EXISTS smoke_alarm_response_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    alarm_id VARCHAR(50) REFERENCES smoke_alarm_state(alarm_id),
    room_id VARCHAR(50) REFERENCES rooms(room_id),
    trigger_condition VARCHAR(50),              -- smoke_level_threshold, alarm_triggered, battery_low
    condition_value FLOAT,                      -- 触发条件的值
    action_type VARCHAR(50),                    -- unlock_door, turn_off_ac, turn_on_lights, send_notification
    action_target VARCHAR(100),                 -- 目标设备ID
    action_params TEXT,                         -- JSON格式的操作参数
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户通知配置表
CREATE TABLE IF NOT EXISTS user_notification_config (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL UNIQUE,
    username VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    notify_on_alarm BOOLEAN DEFAULT true,
    notify_on_low_battery BOOLEAN DEFAULT true,
    notify_on_maintenance_due BOOLEAN DEFAULT true,
    notification_channels TEXT,                 -- JSON: ["email", "sms", "push"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 通知历史表
CREATE TABLE IF NOT EXISTS notification_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    alarm_id VARCHAR(50),
    notification_type VARCHAR(50),              -- alarm, low_battery, maintenance
    channel VARCHAR(20),                        -- email, sms, push
    subject VARCHAR(255),
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'sent',          -- sent, failed, pending
    error_message TEXT
);

-- 设备维护记录表
CREATE TABLE IF NOT EXISTS device_maintenance (
    id SERIAL PRIMARY KEY,
    alarm_id VARCHAR(50) REFERENCES smoke_alarm_state(alarm_id),
    maintenance_type VARCHAR(50),               -- battery_replacement, cleaning, test, inspection
    performed_by VARCHAR(100),
    maintenance_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_maintenance_date TIMESTAMP,
    notes TEXT,
    cost DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 报警确认记录表
CREATE TABLE IF NOT EXISTS alarm_acknowledgments (
    id SERIAL PRIMARY KEY,
    alarm_id VARCHAR(50) NOT NULL,
    event_id INTEGER REFERENCES smoke_alarm_events(id),
    acknowledged_by VARCHAR(100) NOT NULL,
    acknowledged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time INTEGER,                      -- 响应时间（秒）
    action_taken TEXT,                          -- 采取的行动
    resolution VARCHAR(50),                     -- false_alarm, real_fire, resolved, under_investigation
    notes TEXT
);

-- 报警统计表（按天统计）
CREATE TABLE IF NOT EXISTS alarm_statistics (
    id SERIAL PRIMARY KEY,
    alarm_id VARCHAR(50),
    room_id VARCHAR(50),
    stat_date DATE,
    total_alarms INTEGER DEFAULT 0,
    false_alarms INTEGER DEFAULT 0,
    real_alarms INTEGER DEFAULT 0,
    avg_response_time INTEGER,                  -- 平均响应时间（秒）
    max_smoke_level FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(alarm_id, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_lighting_events_light_time
ON lighting_events(light_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_smoke_alarm_events_alarm_time
ON smoke_alarm_events(alarm_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_smoke_alarm_rules_alarm
ON smoke_alarm_response_rules(alarm_id, enabled);

CREATE INDEX IF NOT EXISTS idx_notification_history_user_time
ON notification_history(user_id, sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_device_maintenance_alarm
ON device_maintenance(alarm_id, maintenance_date DESC);

CREATE INDEX IF NOT EXISTS idx_alarm_ack_alarm_time
ON alarm_acknowledgments(alarm_id, acknowledged_at DESC);

-- 初始化灯具状态（统一房间命名）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM lighting_state WHERE light_id = 'light_living') THEN
        INSERT INTO lighting_state (light_id, device_id, power, brightness, auto_mode, color_temp)
        VALUES ('light_living', 'living', false, 50, false, 4000);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM lighting_state WHERE light_id = 'light_bedroom1') THEN
        INSERT INTO lighting_state (light_id, device_id, power, brightness, auto_mode, color_temp)
        VALUES ('light_bedroom1', 'bedroom1', false, 50, false, 4000);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM lighting_state WHERE light_id = 'light_bedroom2') THEN
        INSERT INTO lighting_state (light_id, device_id, power, brightness, auto_mode, color_temp)
        VALUES ('light_bedroom2', 'bedroom2', false, 50, false, 4000);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM lighting_state WHERE light_id = 'light_kitchen') THEN
        INSERT INTO lighting_state (light_id, device_id, power, brightness, auto_mode, color_temp)
        VALUES ('light_kitchen', 'kitchen', false, 50, false, 4000);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_smoke_alarm_events_alarm_time
ON smoke_alarm_events(alarm_id, timestamp DESC);

-- 初始化烟雾报警器（统一房间命名）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM smoke_alarm_state WHERE alarm_id = 'smoke_living') THEN
        INSERT INTO smoke_alarm_state (alarm_id, room_id, location, smoke_level, alarm_active, battery, sensitivity, installation_date, device_model, firmware_version)
        VALUES ('smoke_living', 'living', 'living', 0.0, false, 100, 'medium', NOW(), 'SA-2024-Pro', '1.0.0');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM smoke_alarm_state WHERE alarm_id = 'smoke_bedroom1') THEN
        INSERT INTO smoke_alarm_state (alarm_id, room_id, location, smoke_level, alarm_active, battery, sensitivity, installation_date, device_model, firmware_version)
        VALUES ('smoke_bedroom1', 'bedroom1', 'bedroom1', 0.0, false, 100, 'medium', NOW(), 'SA-2024-Pro', '1.0.0');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM smoke_alarm_state WHERE alarm_id = 'smoke_bedroom2') THEN
        INSERT INTO smoke_alarm_state (alarm_id, room_id, location, smoke_level, alarm_active, battery, sensitivity, installation_date, device_model, firmware_version)
        VALUES ('smoke_bedroom2', 'bedroom2', 'bedroom2', 0.0, false, 100, 'medium', NOW(), 'SA-2024-Pro', '1.0.0');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM smoke_alarm_state WHERE alarm_id = 'smoke_kitchen') THEN
        INSERT INTO smoke_alarm_state (alarm_id, room_id, location, smoke_level, alarm_active, battery, sensitivity, installation_date, device_model, firmware_version)
        VALUES ('smoke_kitchen', 'kitchen', 'kitchen', 0.0, false, 100, 'high', NOW(), 'SA-2024-Pro', '1.0.0');
    END IF;
END $$;

-- 插入示例自动化规则
INSERT INTO smoke_alarm_response_rules (rule_name, alarm_id, room_id, trigger_condition, condition_value, action_type, action_target, action_params, enabled, priority)
VALUES
    ('厨房烟雾报警-自动解锁前门', 'smoke_kitchen', 'kitchen', 'alarm_triggered', 1, 'unlock_door', 'FRONT_DOOR', '{"reason": "emergency_evacuation"}', true, 1),
    ('厨房烟雾报警-关闭空调', 'smoke_kitchen', 'kitchen', 'alarm_triggered', 1, 'turn_off_ac', 'ac_kitchen', '{"prevent_smoke_spread": true}', true, 2),
    ('客厅烟雾报警-打开照明', 'smoke_living', 'living', 'alarm_triggered', 1, 'turn_on_lights', 'light_living', '{"brightness": 100, "reason": "emergency_lighting"}', true, 1);

-- 插入示例用户通知配置
INSERT INTO user_notification_config (user_id, username, email, phone, notify_on_alarm, notify_on_low_battery, notification_channels)
VALUES
    ('admin', '系统管理员', 'admin@smarthome.com', '13800138000', true, true, '["email", "sms"]'),
    ('user1', '张三', 'zhangsan@example.com', '13900139000', true, false, '["email"]');

-- 插入示例维护记录
INSERT INTO device_maintenance (alarm_id, maintenance_type, performed_by, maintenance_date, next_maintenance_date, notes, cost)
VALUES
    ('smoke_living', 'inspection', '技术人员-李四', NOW() - INTERVAL '30 days', NOW() + INTERVAL '335 days', '年度检查，设备状态良好', 50.00),
    ('smoke_bedroom1', 'battery_replacement', '技术人员-王五', NOW() - INTERVAL '180 days', NOW() + INTERVAL '545 days', '更换9V电池', 15.00);

-- 插入初始化事件
INSERT INTO lighting_events (light_id, event_type, detail)
VALUES
    ('light_living', 'INIT', 'Lighting initialized'),
    ('light_bedroom1', 'INIT', 'Lighting initialized'),
    ('light_bedroom2', 'INIT', 'Lighting initialized'),
    ('light_kitchen', 'INIT', 'Lighting initialized');
INSERT INTO smoke_alarm_events (alarm_id, event_type, smoke_level, detail)
VALUES
    ('smoke_living', 'INIT', 0.0, 'Smoke alarm initialized'),
    ('smoke_bedroom1', 'INIT', 0.0, 'Smoke alarm initialized'),
    ('smoke_bedroom2', 'INIT', 0.0, 'Smoke alarm initialized'),
    ('smoke_kitchen', 'INIT', 0.0, 'Smoke alarm initialized');

-- 完成提示
SELECT '✓ Database initialization completed!' AS status;
SELECT 'Database: smart_home' AS info;
SELECT 'Tables: temperature_humidity_data, lock_state, lock_events, ac_state, ac_events, lighting_state, lighting_events, smoke_alarm_state, smoke_alarm_events' AS info;
SELECT 'Rooms: living, bedroom1, bedroom2, kitchen' AS info;
SELECT 'Devices: ac_living, ac_bedroom1, ac_bedroom2, ac_kitchen, light_living, light_bedroom1, light_bedroom2, light_kitchen, smoke_living, smoke_bedroom1, smoke_bedroom2, smoke_kitchen' AS info;
SELECT COUNT(*) || ' test records inserted' AS info FROM temperature_humidity_data;
