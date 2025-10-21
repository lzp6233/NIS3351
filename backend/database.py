"""
数据库操作模块（使用 py-opengauss）
支持 openGauss 的 SCRAM-SHA-256 认证
"""

import py_opengauss
import sqlite3
from config import DB_CONFIG, DB_TYPE, DB_PATH


def get_connection():
    """
    获取数据库连接
    使用 py-opengauss，openGauss 官方驱动
    """
    # 支持 sqlite 回退，便于在本地 macOS 上快速测试
    if DB_TYPE == 'sqlite':
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = None
        # 自动建表：温湿度、门锁（本地开发零依赖）
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS temperature_humidity_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id VARCHAR(50) DEFAULT 'room1',
                temperature FLOAT NOT NULL,
                humidity FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lock_state (
                lock_id VARCHAR(50) PRIMARY KEY,
                locked BOOLEAN NOT NULL,
                method VARCHAR(20),
                actor VARCHAR(64),
                battery INTEGER DEFAULT 100,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lock_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lock_id VARCHAR(50) NOT NULL,
                event_type VARCHAR(32) NOT NULL,
                method VARCHAR(20),
                actor VARCHAR(64),
                detail TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return conn

    # 构建连接字符串: opengauss://user:password@host:port/database
    conn_string = f"opengauss://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    conn = py_opengauss.open(conn_string)
    return conn


def insert_sensor_data(data, device_id='room1'):
    """插入温湿度传感器数据"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO temperature_humidity_data (device_id, temperature, humidity, timestamp) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (device_id, data.get("temperature"), data.get("humidity"))
            )
            conn.commit()
        else:
            stmt = conn.prepare(
                "INSERT INTO temperature_humidity_data (device_id, temperature, humidity) VALUES ($1, $2, $3)"
            )
            stmt(device_id, data["temperature"], data["humidity"])
    finally:
        conn.close()


def get_recent_data(device_id=None, limit=100):
    """获取最近的温湿度数据"""
    conn = get_connection()
    try:
        result = []
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            if device_id:
                cur.execute(
                    "SELECT id, device_id, temperature, humidity, timestamp FROM temperature_humidity_data WHERE device_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (device_id, limit)
                )
            else:
                cur.execute(
                    "SELECT id, device_id, temperature, humidity, timestamp FROM temperature_humidity_data ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
            rows = cur.fetchall()
            for row in rows:
                # sqlite returns timestamp as text; keep as-is
                result.append({
                    'id': row[0],
                    'device_id': row[1],
                    'temperature': row[2],
                    'humidity': row[3],
                    'timestamp': row[4]
                })
            return result

        # openGauss path
        if device_id:
            stmt = conn.prepare("""
                SELECT id, device_id, temperature, humidity, timestamp 
                FROM temperature_humidity_data 
                WHERE device_id = $1
                ORDER BY timestamp DESC 
                LIMIT $2
            """)
            rows = stmt(device_id, limit)
        else:
            stmt = conn.prepare("""
                SELECT id, device_id, temperature, humidity, timestamp 
                FROM temperature_humidity_data 
                ORDER BY timestamp DESC 
                LIMIT $1
            """)
            rows = stmt(limit)
        
        for row in rows:
            result.append({
                'id': row[0],
                'device_id': row[1],
                'temperature': row[2],
                'humidity': row[3],
                'timestamp': row[4].isoformat() if row[4] else None
            })
        return result
    finally:
        conn.close()


def get_devices():
    """获取所有设备列表"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT device_id, COUNT(*) as count FROM temperature_humidity_data GROUP BY device_id ORDER BY device_id"
            )
            rows = cur.fetchall()
            return [{'device_id': row[0], 'data_count': row[1]} for row in rows]

        rows = conn.query("""
            SELECT DISTINCT device_id, COUNT(*) as count
            FROM temperature_humidity_data
            GROUP BY device_id
            ORDER BY device_id
        """)
        return [{'device_id': row[0], 'data_count': row[1]} for row in rows]
    finally:
        conn.close()


def get_latest_data(device_id):
    """获取指定设备的最新数据"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT id, device_id, temperature, humidity, timestamp FROM temperature_humidity_data WHERE device_id = ? ORDER BY timestamp DESC LIMIT 1",
                (device_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    'id': row[0],
                    'device_id': row[1],
                    'temperature': row[2],
                    'humidity': row[3],
                    'timestamp': row[4]
                }
            return None

        stmt = conn.prepare("""
            SELECT id, device_id, temperature, humidity, timestamp 
            FROM temperature_humidity_data 
            WHERE device_id = $1
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        rows = stmt(device_id)
        if rows:
            row = rows[0]
            return {
                'id': row[0],
                'device_id': row[1],
                'temperature': row[2],
                'humidity': row[3],
                'timestamp': row[4].isoformat() if row[4] else None
            }
        return None
    finally:
        conn.close()


def upsert_lock_state(lock_id, locked, method=None, actor=None, battery=None, ts=None):
    """插入或更新锁的当前状态（单行）。"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            # 确保表存在（本地快速开发时）
            cur.execute("""
                CREATE TABLE IF NOT EXISTS lock_state (
                    lock_id VARCHAR(50) PRIMARY KEY,
                    locked BOOLEAN NOT NULL,
                    method VARCHAR(20),
                    actor VARCHAR(64),
                    battery INTEGER DEFAULT 100,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # upsert
            cur.execute("""
                INSERT INTO lock_state (lock_id, locked, method, actor, battery, updated_at)
                VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                ON CONFLICT(lock_id) DO UPDATE SET
                    locked=excluded.locked,
                    method=excluded.method,
                    actor=excluded.actor,
                    battery=excluded.battery,
                    updated_at=excluded.updated_at
            """, (lock_id, bool(locked), method, actor, battery if battery is not None else 100, ts))
            conn.commit()
            return True

        # openGauss - 使用 MERGE 语句替代 ON CONFLICT，处理时间戳类型转换
        try:
            # 处理时间戳参数 - 如果已经是字符串则直接使用，否则转换为字符串格式
            if isinstance(ts, str):
                ts_str = ts
            elif ts is not None:
                ts_str = ts.isoformat()
            else:
                ts_str = None
            
            # 先尝试更新
            update_stmt = conn.prepare("""
                UPDATE lock_state 
                SET locked = $2, method = $3, actor = $4, battery = COALESCE($5, 100), 
                    updated_at = COALESCE($6::text::timestamp, CURRENT_TIMESTAMP)
                WHERE lock_id = $1
            """)
            result = update_stmt(lock_id, bool(locked), method, actor, battery, ts_str)
            
            # 如果没有更新任何行，则插入新行
            if result.rowcount == 0:
                insert_stmt = conn.prepare("""
                    INSERT INTO lock_state (lock_id, locked, method, actor, battery, updated_at)
                    VALUES ($1, $2, $3, $4, COALESCE($5, 100), COALESCE($6::text::timestamp, CURRENT_TIMESTAMP))
                """)
                insert_stmt(lock_id, bool(locked), method, actor, battery, ts_str)
        except Exception as e:
            # 如果插入失败（可能是并发插入），再次尝试更新
            if isinstance(ts, str):
                ts_str = ts
            elif ts is not None:
                ts_str = ts.isoformat()
            else:
                ts_str = None
            update_stmt = conn.prepare("""
                UPDATE lock_state 
                SET locked = $2, method = $3, actor = $4, battery = COALESCE($5, 100), 
                    updated_at = COALESCE($6::text::timestamp, CURRENT_TIMESTAMP)
                WHERE lock_id = $1
            """)
            update_stmt(lock_id, bool(locked), method, actor, battery, ts_str)
        
        return True
    finally:
        conn.close()


def insert_lock_event(lock_id, event_type, method=None, actor=None, detail=None, ts=None):
    """写入锁事件流水。"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS lock_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lock_id VARCHAR(50) NOT NULL,
                    event_type VARCHAR(32) NOT NULL,
                    method VARCHAR(20),
                    actor VARCHAR(64),
                    detail TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                INSERT INTO lock_events (lock_id, event_type, method, actor, detail, timestamp)
                VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """, (lock_id, event_type, method, actor, detail, ts))
            conn.commit()
            return True

        stmt = conn.prepare("""
            INSERT INTO lock_events (lock_id, event_type, method, actor, detail, timestamp)
            VALUES ($1, $2, $3, $4, $5, COALESCE($6, CURRENT_TIMESTAMP))
        """)
        stmt(lock_id, event_type, method, actor, detail, ts)
        return True
    finally:
        conn.close()


def get_lock_state(lock_id):
    """读取某把锁的当前状态。"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("SELECT lock_id, locked, method, actor, battery, updated_at FROM lock_state WHERE lock_id = ?", (lock_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                'lock_id': row[0],
                'locked': bool(row[1]),
                'method': row[2],
                'actor': row[3],
                'battery': row[4],
                'updated_at': row[5]
            }

        stmt = conn.prepare("""
            SELECT lock_id, locked, method, actor, battery, updated_at
            FROM lock_state WHERE lock_id = $1
        """)
        rows = stmt(lock_id)
        if not rows:
            return None
        row = rows[0]
        return {
            'lock_id': row[0],
            'locked': bool(row[1]),
            'method': row[2],
            'actor': row[3],
            'battery': row[4],
            'updated_at': row[5].isoformat() if row[5] else None
        }
    finally:
        conn.close()


def get_all_locks():
    """列出所有锁。"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("SELECT lock_id, locked, method, actor, battery, updated_at FROM lock_state ORDER BY lock_id")
            rows = cur.fetchall()
            return [
                {
                    'lock_id': r[0], 'locked': bool(r[1]), 'method': r[2], 'actor': r[3],
                    'battery': r[4], 'updated_at': r[5]
                } for r in rows
            ]

        rows = conn.query("""
            SELECT lock_id, locked, method, actor, battery, updated_at
            FROM lock_state ORDER BY lock_id
        """)
        result = []
        for row in rows:
            result.append({
                'lock_id': row[0],
                'locked': bool(row[1]),
                'method': row[2],
                'actor': row[3],
                'battery': row[4],
                'updated_at': row[5].isoformat() if row[5] else None
            })
        return result
    finally:
        conn.close()


def get_lock_events(lock_id, limit=50):
    """读取最近的锁事件。"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, lock_id, event_type, method, actor, detail, timestamp
                FROM lock_events WHERE lock_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (lock_id, limit)
            )
            rows = cur.fetchall()
            return [
                {
                    'id': r[0], 'lock_id': r[1], 'event_type': r[2], 'method': r[3],
                    'actor': r[4], 'detail': r[5], 'timestamp': r[6]
                } for r in rows
            ]

        stmt = conn.prepare("""
            SELECT id, lock_id, event_type, method, actor, detail, timestamp
            FROM lock_events WHERE lock_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
        """)
        rows = stmt(lock_id, limit)
        result = []
        for r in rows:
            result.append({
                'id': r[0], 'lock_id': r[1], 'event_type': r[2], 'method': r[3],
                'actor': r[4], 'detail': r[5], 'timestamp': r[6].isoformat() if r[6] else None
            })
        return result
    finally:
        conn.close()
