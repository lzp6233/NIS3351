-- ============================================
-- 仅初始化空调表和数据
-- 使用方法：gsql -d smart_home -h 127.0.0.1 -p 7654 -U lzp -W <password> -f init_ac_only.sql
-- ============================================

-- 连接到数据库
\c smart_home

-- 创建空调状态表
SELECT 'Creating ac_state table...' AS status;

CREATE TABLE IF NOT EXISTS ac_state (
    ac_id VARCHAR(50) PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    power BOOLEAN DEFAULT false,
    mode VARCHAR(20) DEFAULT 'cool',
    target_temp FLOAT DEFAULT 26.0,
    current_temp FLOAT,
    current_humidity FLOAT,
    fan_speed VARCHAR(20) DEFAULT 'auto',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建空调事件表
SELECT 'Creating ac_events table...' AS status;

CREATE TABLE IF NOT EXISTS ac_events (
    id SERIAL PRIMARY KEY,
    ac_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    detail TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ac_events_ac_time
ON ac_events(ac_id, timestamp DESC);

-- 初始化空调数据
SELECT 'Initializing air conditioner data...' AS status;

DO $$
BEGIN
    -- 初始化 ac_room1
    IF NOT EXISTS (SELECT 1 FROM ac_state WHERE ac_id = 'ac_room1') THEN
        INSERT INTO ac_state (ac_id, device_id, power, mode, target_temp, fan_speed)
        VALUES ('ac_room1', 'room1', false, 'cool', 26.0, 'auto');
        RAISE NOTICE 'Created ac_room1';
    ELSE
        RAISE NOTICE 'ac_room1 already exists';
    END IF;
    
    -- 初始化 ac_room2
    IF NOT EXISTS (SELECT 1 FROM ac_state WHERE ac_id = 'ac_room2') THEN
        INSERT INTO ac_state (ac_id, device_id, power, mode, target_temp, fan_speed)
        VALUES ('ac_room2', 'room2', false, 'cool', 26.0, 'auto');
        RAISE NOTICE 'Created ac_room2';
    ELSE
        RAISE NOTICE 'ac_room2 already exists';
    END IF;
END $$;

-- 插入初始化事件
INSERT INTO ac_events (ac_id, event_type, detail)
SELECT 'ac_room1', 'INIT', 'Air conditioner initialized'
WHERE NOT EXISTS (SELECT 1 FROM ac_events WHERE ac_id = 'ac_room1' AND event_type = 'INIT');

INSERT INTO ac_events (ac_id, event_type, detail)
SELECT 'ac_room2', 'INIT', 'Air conditioner initialized'
WHERE NOT EXISTS (SELECT 1 FROM ac_events WHERE ac_id = 'ac_room2' AND event_type = 'INIT');

-- 显示结果
SELECT '✓ Air conditioner initialization completed!' AS status;

SELECT 'Current air conditioner status:' AS info;
SELECT * FROM ac_state;

SELECT 'Total events:' AS info;
SELECT COUNT(*) as event_count FROM ac_events;

