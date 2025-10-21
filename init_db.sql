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
    method VARCHAR(20),                 -- 开锁方式：PINCODE/FINGERPRINT/APP/REMOTE/KEY
    actor VARCHAR(64),                  -- 操作用户：如 Dad, Guest_123
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

-- 初始化一把大门锁的状态
INSERT INTO lock_state (lock_id, locked, method, actor, battery)
VALUES ('FRONT_DOOR', TRUE, NULL, NULL, 100)
ON CONFLICT (lock_id) DO NOTHING;

-- 插入示例事件
INSERT INTO lock_events (lock_id, event_type, method, actor, detail)
VALUES ('FRONT_DOOR', 'INIT', NULL, NULL, 'Initialized with LOCKED=TRUE');

-- 完成提示
SELECT '✓ Database initialization completed!' AS status;
SELECT 'Database: smart_home' AS info;
SELECT 'Table: temperature_humidity_data, lock_state, lock_events' AS info;
SELECT COUNT(*) || ' test records inserted' AS info FROM temperature_humidity_data;
