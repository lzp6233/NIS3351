-- ============================================
-- NIS3351 智能家居监控系统数据库初始化脚本
-- 使用方法：gsql -d postgres -h 127.0.0.1 -p 7654 -f init_db.sql
-- ============================================

-- 1. 创建数据库（如果不存在）
SELECT 'Creating database...' AS status;
CREATE DATABASE smart_home;

-- 2. 连接到新数据库
\c smart_home

-- 3. 创建温湿度传感器数据表
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

-- 完成提示
SELECT '✓ Database initialization completed!' AS status;
SELECT 'Database: smart_home' AS info;
SELECT 'Tables: temperature_humidity_data, lock_state, lock_events, ac_state, ac_events' AS info;
SELECT COUNT(*) || ' test records inserted' AS info FROM temperature_humidity_data;
