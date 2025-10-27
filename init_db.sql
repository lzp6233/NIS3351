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

-- 初始化空调状态（为每个房间创建一个空调，仅在不存在时插入）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ac_state WHERE ac_id = 'ac_room1') THEN
        INSERT INTO ac_state (ac_id, device_id, power, mode, target_temp, fan_speed)
        VALUES ('ac_room1', 'room1', false, 'cool', 26.0, 'auto');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM ac_state WHERE ac_id = 'ac_room2') THEN
        INSERT INTO ac_state (ac_id, device_id, power, mode, target_temp, fan_speed)
        VALUES ('ac_room2', 'room2', false, 'cool', 26.0, 'auto');
    END IF;
END $$;

-- 插入初始化事件
INSERT INTO ac_events (ac_id, event_type, detail)
VALUES 
    ('ac_room1', 'INIT', 'Air conditioner initialized'),
    ('ac_room2', 'INIT', 'Air conditioner initialized');

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

-- 11. 烟雾报警器：智能烟雾报警器表结构
SELECT 'Creating tables for smoke alarm...' AS status;

-- 烟雾报警器状态表
CREATE TABLE IF NOT EXISTS smoke_alarm_state (
    alarm_id VARCHAR(50) PRIMARY KEY,
    location VARCHAR(50) NOT NULL,              -- 位置：living_room/bedroom/kitchen等
    smoke_level FLOAT DEFAULT 0.0,              -- 烟雾浓度 (0-100)
    alarm_active BOOLEAN DEFAULT false,         -- 报警状态
    battery INTEGER DEFAULT 100,                -- 电池电量百分比
    test_mode BOOLEAN DEFAULT false,            -- 测试模式
    sensitivity VARCHAR(20) DEFAULT 'medium',   -- 灵敏度：low/medium/high
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

CREATE INDEX IF NOT EXISTS idx_lighting_events_light_time
ON lighting_events(light_id, timestamp DESC);

-- 初始化灯具状态（为每个房间创建灯具，仅在不存在时插入）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM lighting_state WHERE light_id = 'light_room1') THEN
        INSERT INTO lighting_state (light_id, device_id, power, brightness, auto_mode, color_temp)
        VALUES ('light_room1', 'room1', false, 50, false, 4000);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM lighting_state WHERE light_id = 'light_room2') THEN
        INSERT INTO lighting_state (light_id, device_id, power, brightness, auto_mode, color_temp)
        VALUES ('light_room2', 'room2', false, 50, false, 4000);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM lighting_state WHERE light_id = 'light_living') THEN
        INSERT INTO lighting_state (light_id, device_id, power, brightness, auto_mode, color_temp)
        VALUES ('light_living', 'living', false, 50, false, 4000);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM lighting_state WHERE light_id = 'light_kitchen') THEN
        INSERT INTO lighting_state (light_id, device_id, power, brightness, auto_mode, color_temp)
        VALUES ('light_kitchen', 'kitchen', false, 50, false, 4000);
CREATE INDEX IF NOT EXISTS idx_smoke_alarm_events_alarm_time
ON smoke_alarm_events(alarm_id, timestamp DESC);

-- 初始化烟雾报警器（为主要房间创建报警器）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM smoke_alarm_state WHERE alarm_id = 'smoke_living_room') THEN
        INSERT INTO smoke_alarm_state (alarm_id, location, smoke_level, alarm_active, battery, sensitivity)
        VALUES ('smoke_living_room', 'living_room', 0.0, false, 100, 'medium');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM smoke_alarm_state WHERE alarm_id = 'smoke_bedroom') THEN
        INSERT INTO smoke_alarm_state (alarm_id, location, smoke_level, alarm_active, battery, sensitivity)
        VALUES ('smoke_bedroom', 'bedroom', 0.0, false, 100, 'medium');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM smoke_alarm_state WHERE alarm_id = 'smoke_kitchen') THEN
        INSERT INTO smoke_alarm_state (alarm_id, location, smoke_level, alarm_active, battery, sensitivity)
        VALUES ('smoke_kitchen', 'kitchen', 0.0, false, 100, 'high');
    END IF;
END $$;

-- 插入初始化事件
INSERT INTO lighting_events (light_id, event_type, detail)
VALUES 
    ('light_room1', 'INIT', 'Lighting initialized'),
    ('light_room2', 'INIT', 'Lighting initialized'),
    ('light_living', 'INIT', 'Lighting initialized'),
    ('light_kitchen', 'INIT', 'Lighting initialized');
INSERT INTO smoke_alarm_events (alarm_id, event_type, smoke_level, detail)
VALUES
    ('smoke_living_room', 'INIT', 0.0, 'Smoke alarm initialized'),
    ('smoke_bedroom', 'INIT', 0.0, 'Smoke alarm initialized'),
    ('smoke_kitchen', 'INIT', 0.0, 'Smoke alarm initialized');

-- 完成提示
SELECT '✓ Database initialization completed!' AS status;
SELECT 'Database: smart_home' AS info;
SELECT 'Tables: temperature_humidity_data, lock_state, lock_events, ac_state, ac_events, lighting_state, lighting_events' AS info;
SELECT 'Tables: temperature_humidity_data, lock_state, lock_events, ac_state, ac_events, smoke_alarm_state, smoke_alarm_events' AS info;
SELECT COUNT(*) || ' test records inserted' AS info FROM temperature_humidity_data;
