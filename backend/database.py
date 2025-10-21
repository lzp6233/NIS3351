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
        # 空调状态表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ac_state (
                ac_id VARCHAR(50) PRIMARY KEY,
                device_id VARCHAR(50) NOT NULL,
                power BOOLEAN DEFAULT 0,
                mode VARCHAR(20) DEFAULT 'cool',
                target_temp FLOAT DEFAULT 26.0,
                current_temp FLOAT,
                current_humidity FLOAT,
                fan_speed VARCHAR(20) DEFAULT 'auto',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 空调事件表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ac_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ac_id VARCHAR(50) NOT NULL,
                event_type VARCHAR(32) NOT NULL,
                old_value TEXT,
                new_value TEXT,
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
                    "id": row[0],
                    "device_id": row[1],
                    "temperature": row[2],
                    "humidity": row[3],
                    "timestamp": row[4]
                })
            return result

        if device_id:
            stmt = conn.prepare(
                "SELECT id, device_id, temperature, humidity, timestamp FROM temperature_humidity_data WHERE device_id = $1 ORDER BY timestamp DESC LIMIT $2"
            )
            rows = stmt(device_id, limit)
        else:
            stmt = conn.prepare(
                "SELECT id, device_id, temperature, humidity, timestamp FROM temperature_humidity_data ORDER BY timestamp DESC LIMIT $1"
            )
            rows = stmt(limit)

        for row in rows:
            result.append({
                "id": row[0],
                "device_id": row[1],
                "temperature": row[2],
                "humidity": row[3],
                "timestamp": row[4].isoformat() if row[4] else None
            })
        return result
    finally:
        conn.close()


def get_devices():
    """获取所有设备列表及其数据数量"""
    conn = get_connection()
    try:
        result = []
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT device_id, COUNT(*) as count FROM temperature_humidity_data GROUP BY device_id"
            )
            rows = cur.fetchall()
            for row in rows:
                result.append({
                    "device_id": row[0],
                    "data_count": row[1]
                })
            return result

        stmt = conn.prepare(
            "SELECT device_id, COUNT(*) as count FROM temperature_humidity_data GROUP BY device_id"
        )
        rows = stmt()
        for row in rows:
            result.append({
                "device_id": row[0],
                "data_count": row[1]
            })
        return result
    finally:
        conn.close()


def get_latest_data(device_id):
    """获取指定设备的最新一条数据"""
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
                    "id": row[0],
                    "device_id": row[1],
                    "temperature": row[2],
                    "humidity": row[3],
                    "timestamp": row[4]
                }
            return None

        stmt = conn.prepare(
            "SELECT id, device_id, temperature, humidity, timestamp FROM temperature_humidity_data WHERE device_id = $1 ORDER BY timestamp DESC LIMIT 1"
        )
        rows = stmt(device_id)
        for row in rows:
            return {
                "id": row[0],
                "device_id": row[1],
                "temperature": row[2],
                "humidity": row[3],
                "timestamp": row[4].isoformat() if row[4] else None
            }
        return None
    finally:
        conn.close()


# ==================== 门锁功能 ====================

def upsert_lock_state(lock_id, locked, method=None, actor=None, battery=None, ts=None):
    """更新或插入门锁状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            # 检查是否存在
            cur.execute("SELECT lock_id FROM lock_state WHERE lock_id = ?", (lock_id,))
            exists = cur.fetchone()

            if exists:
                # 更新
                cur.execute(
                    """UPDATE lock_state
                       SET locked=?, method=?, actor=?, battery=?, updated_at=CURRENT_TIMESTAMP
                       WHERE lock_id=?""",
                    (1 if locked else 0, method, actor, battery, lock_id)
                )
            else:
                # 插入
                cur.execute(
                    """INSERT INTO lock_state (lock_id, locked, method, actor, battery)
                       VALUES (?, ?, ?, ?, ?)""",
                    (lock_id, 1 if locked else 0, method, actor, battery or 100)
                )
            conn.commit()
            return

        # openGauss 不支持 ON CONFLICT，需要先查询再决定插入或更新
        stmt_check = conn.prepare("SELECT lock_id FROM lock_state WHERE lock_id = $1")
        rows = stmt_check(lock_id)
        exists = False
        for _ in rows:
            exists = True
            break
        
        if exists:
            # 更新
            stmt = conn.prepare("""
                UPDATE lock_state
                SET locked=$2, method=$3, actor=$4, battery=$5, updated_at=NOW()
                WHERE lock_id=$1
            """)
            stmt(lock_id, locked, method, actor, battery or 100)
        else:
            # 插入
            stmt = conn.prepare("""
                INSERT INTO lock_state (lock_id, locked, method, actor, battery, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
            """)
            stmt(lock_id, locked, method, actor, battery or 100)
    finally:
        conn.close()


def get_lock_state(lock_id):
    """获取门锁状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT lock_id, locked, method, actor, battery, updated_at FROM lock_state WHERE lock_id = ?",
                (lock_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    'lock_id': row[0],
                    'locked': bool(row[1]),
                    'method': row[2],
                    'actor': row[3],
                    'battery': row[4],
                    'updated_at': row[5]
                }
            return None

        stmt = conn.prepare(
            "SELECT lock_id, locked, method, actor, battery, updated_at FROM lock_state WHERE lock_id = $1"
        )
        rows = stmt(lock_id)
        for r in rows:
            return {
                'lock_id': r[0],
                'locked': r[1],
                'method': r[2],
                'actor': r[3],
                'battery': r[4],
                'updated_at': r[5].isoformat() if r[5] else None
            }
        return None
    finally:
        conn.close()


def get_all_locks():
    """获取所有门锁状态"""
    conn = get_connection()
    try:
        result = []
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT lock_id, locked, method, actor, battery, updated_at FROM lock_state"
            )
            rows = cur.fetchall()
            for r in rows:
                result.append({
                    'lock_id': r[0],
                    'locked': bool(r[1]),
                    'method': r[2],
                    'actor': r[3],
                    'battery': r[4],
                    'updated_at': r[5]
                })
            return result

        stmt = conn.prepare(
            "SELECT lock_id, locked, method, actor, battery, updated_at FROM lock_state"
        )
        rows = stmt()
        for r in rows:
            result.append({
                'lock_id': r[0],
                'locked': r[1],
                'method': r[2],
                'actor': r[3],
                'battery': r[4],
                'updated_at': r[5].isoformat() if r[5] else None
            })
        return result
    finally:
        conn.close()


def insert_lock_event(lock_id, event_type, method=None, actor=None, detail=None, ts=None):
    """插入门锁事件"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO lock_events (lock_id, event_type, method, actor, detail)
                   VALUES (?, ?, ?, ?, ?)""",
                (lock_id, event_type, method, actor, detail)
            )
            conn.commit()
            return

        stmt = conn.prepare("""
            INSERT INTO lock_events (lock_id, event_type, method, actor, detail, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6)
        """)
        stmt(lock_id, event_type, method, actor, detail, ts)
    finally:
        conn.close()


def get_lock_events(lock_id, limit=50):
    """获取门锁事件历史"""
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


# ==================== 空调控制功能 ====================

def upsert_ac_state(ac_id, device_id='room1', power=None, mode=None, target_temp=None, 
                    current_temp=None, current_humidity=None, fan_speed=None):
    """更新或插入空调状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            # 检查是否存在
            cur.execute("SELECT ac_id FROM ac_state WHERE ac_id = ?", (ac_id,))
            exists = cur.fetchone()
            
            if exists:
                # 更新
                updates = []
                values = []
                if power is not None:
                    updates.append("power = ?")
                    values.append(1 if power else 0)
                if mode is not None:
                    updates.append("mode = ?")
                    values.append(mode)
                if target_temp is not None:
                    updates.append("target_temp = ?")
                    values.append(target_temp)
                if current_temp is not None:
                    updates.append("current_temp = ?")
                    values.append(current_temp)
                if current_humidity is not None:
                    updates.append("current_humidity = ?")
                    values.append(current_humidity)
                if fan_speed is not None:
                    updates.append("fan_speed = ?")
                    values.append(fan_speed)
                
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    values.append(ac_id)
                    sql = f"UPDATE ac_state SET {', '.join(updates)} WHERE ac_id = ?"
                    cur.execute(sql, values)
            else:
                # 插入
                cur.execute(
                    """INSERT INTO ac_state 
                       (ac_id, device_id, power, mode, target_temp, current_temp, current_humidity, fan_speed)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (ac_id, device_id, 
                     1 if power else 0, 
                     mode or 'cool', 
                     target_temp or 26.0,
                     current_temp, current_humidity, 
                     fan_speed or 'auto')
                )
            conn.commit()
        else:
            # openGauss 处理
            # 先检查是否存在
            stmt_check = conn.prepare("SELECT ac_id FROM ac_state WHERE ac_id = $1")
            rows = stmt_check(ac_id)
            exists = False
            for _ in rows:
                exists = True
                break
            
            if exists:
                # 更新
                updates = []
                values = [ac_id]  # WHERE ac_id = $1
                param_count = 2
                
                if power is not None:
                    updates.append(f"power = ${param_count}")
                    values.append(power)
                    param_count += 1
                if mode is not None:
                    updates.append(f"mode = ${param_count}")
                    values.append(mode)
                    param_count += 1
                if target_temp is not None:
                    updates.append(f"target_temp = ${param_count}")
                    values.append(target_temp)
                    param_count += 1
                if current_temp is not None:
                    updates.append(f"current_temp = ${param_count}")
                    values.append(current_temp)
                    param_count += 1
                if current_humidity is not None:
                    updates.append(f"current_humidity = ${param_count}")
                    values.append(current_humidity)
                    param_count += 1
                if fan_speed is not None:
                    updates.append(f"fan_speed = ${param_count}")
                    values.append(fan_speed)
                    param_count += 1
                
                if updates:
                    updates.append("updated_at = NOW()")
                    sql = f"UPDATE ac_state SET {', '.join(updates)} WHERE ac_id = $1"
                    stmt = conn.prepare(sql)
                    stmt(*values)
            else:
                # 插入
                stmt = conn.prepare("""
                    INSERT INTO ac_state 
                    (ac_id, device_id, power, mode, target_temp, current_temp, current_humidity, fan_speed, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """)
                stmt(ac_id, device_id, power or False, mode or 'cool', 
                     target_temp or 26.0, current_temp, current_humidity, fan_speed or 'auto')
    finally:
        conn.close()


def get_ac_state(ac_id):
    """获取空调状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """SELECT ac_id, device_id, power, mode, target_temp, current_temp, 
                          current_humidity, fan_speed, updated_at
                   FROM ac_state WHERE ac_id = ?""",
                (ac_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    'ac_id': row[0],
                    'device_id': row[1],
                    'power': bool(row[2]),
                    'mode': row[3],
                    'target_temp': row[4],
                    'current_temp': row[5],
                    'current_humidity': row[6],
                    'fan_speed': row[7],
                    'updated_at': row[8]
                }
            return None
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                SELECT ac_id, device_id, power, mode, target_temp, current_temp,
                       current_humidity, fan_speed, updated_at
                FROM ac_state WHERE ac_id = $1
            """)
            rows = stmt(ac_id)
            for row in rows:
                return {
                    'ac_id': row[0],
                    'device_id': row[1],
                    'power': bool(row[2]),
                    'mode': row[3],
                    'target_temp': row[4],
                    'current_temp': row[5],
                    'current_humidity': row[6],
                    'fan_speed': row[7],
                    'updated_at': row[8].isoformat() if row[8] else None
                }
            return None
    finally:
        conn.close()


def get_all_acs():
    """获取所有空调状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """SELECT ac_id, device_id, power, mode, target_temp, current_temp,
                          current_humidity, fan_speed, updated_at
                   FROM ac_state"""
            )
            rows = cur.fetchall()
            return [
                {
                    'ac_id': r[0],
                    'device_id': r[1],
                    'power': bool(r[2]),
                    'mode': r[3],
                    'target_temp': r[4],
                    'current_temp': r[5],
                    'current_humidity': r[6],
                    'fan_speed': r[7],
                    'updated_at': r[8]
                } for r in rows
            ]
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                SELECT ac_id, device_id, power, mode, target_temp, current_temp,
                       current_humidity, fan_speed, updated_at
                FROM ac_state
            """)
            rows = stmt()
            result = []
            for r in rows:
                result.append({
                    'ac_id': r[0],
                    'device_id': r[1],
                    'power': bool(r[2]),
                    'mode': r[3],
                    'target_temp': r[4],
                    'current_temp': r[5],
                    'current_humidity': r[6],
                    'fan_speed': r[7],
                    'updated_at': r[8].isoformat() if r[8] else None
                })
            return result
    finally:
        conn.close()


def insert_ac_event(ac_id, event_type, old_value=None, new_value=None, detail=None):
    """记录空调事件"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO ac_events (ac_id, event_type, old_value, new_value, detail)
                   VALUES (?, ?, ?, ?, ?)""",
                (ac_id, event_type, old_value, new_value, detail)
            )
            conn.commit()
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                INSERT INTO ac_events (ac_id, event_type, old_value, new_value, detail, timestamp)
                VALUES ($1, $2, $3, $4, $5, NOW())
            """)
            stmt(ac_id, event_type, old_value, new_value, detail)
    finally:
        conn.close()


def get_ac_events(ac_id, limit=50):
    """获取空调事件历史"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """SELECT id, ac_id, event_type, old_value, new_value, detail, timestamp
                   FROM ac_events WHERE ac_id = ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (ac_id, limit)
            )
            rows = cur.fetchall()
            return [
                {
                    'id': r[0],
                    'ac_id': r[1],
                    'event_type': r[2],
                    'old_value': r[3],
                    'new_value': r[4],
                    'detail': r[5],
                    'timestamp': r[6]
                } for r in rows
            ]
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                SELECT id, ac_id, event_type, old_value, new_value, detail, timestamp
                FROM ac_events WHERE ac_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """)
            rows = stmt(ac_id, limit)
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'ac_id': r[1],
                    'event_type': r[2],
                    'old_value': r[3],
                    'new_value': r[4],
                    'detail': r[5],
                    'timestamp': r[6].isoformat() if r[6] else None
                })
            return result
    finally:
        conn.close()
