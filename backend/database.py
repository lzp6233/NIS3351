"""
数据库操作模块（使用 py-opengauss）
支持 openGauss 的 SCRAM-SHA-256 认证
"""

import sqlite3
from config import DB_CONFIG, DB_TYPE, DB_PATH
import py_opengauss


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
        # 用户认证表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lock_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                pincode VARCHAR(10) NOT NULL,
                face_image_path VARCHAR(255),
                fingerprint_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 自动锁定配置表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lock_auto_config (
                lock_id VARCHAR(50) PRIMARY KEY,
                auto_lock_enabled BOOLEAN DEFAULT 1,
                auto_lock_delay INTEGER DEFAULT 5,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        # 灯具状态表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lighting_state (
                light_id VARCHAR(50) PRIMARY KEY,
                device_id VARCHAR(50) NOT NULL,
                power BOOLEAN DEFAULT 0,
                brightness INTEGER DEFAULT 50,
                auto_mode BOOLEAN DEFAULT 0,
                room_brightness FLOAT,
                color_temp INTEGER DEFAULT 4000,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 灯具事件表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lighting_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                light_id VARCHAR(50) NOT NULL,
                event_type VARCHAR(32) NOT NULL,
                old_value TEXT,
                new_value TEXT,
                detail TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 烟雾报警器状态表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS smoke_alarm_state (
                alarm_id VARCHAR(50) PRIMARY KEY,
                location VARCHAR(50) NOT NULL,
                smoke_level FLOAT DEFAULT 0.0,
                alarm_active BOOLEAN DEFAULT 0,
                battery INTEGER DEFAULT 100,
                test_mode BOOLEAN DEFAULT 0,
                sensitivity VARCHAR(20) DEFAULT 'medium',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 烟雾报警器事件表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS smoke_alarm_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alarm_id VARCHAR(50) NOT NULL,
                event_type VARCHAR(32) NOT NULL,
                smoke_level FLOAT,
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


# ==================== 用户认证功能 ====================

def create_lock_user(username, password, pincode, face_image_path=None, fingerprint_data=None):
    """创建门锁用户"""
    import hashlib
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO lock_users (username, password_hash, encrypted_pincode, face_image_path, fingerprint_data)
                   VALUES (?, ?, ?, ?, ?)""",
                (username, password_hash, pincode, face_image_path, fingerprint_data)
            )
            conn.commit()
        else:
            stmt = conn.prepare("""
                INSERT INTO lock_users (username, password_hash, pincode, face_image_path, fingerprint_data, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            """)
            stmt(username, password_hash, pincode, face_image_path, fingerprint_data)
    finally:
        conn.close()


def get_all_lock_users():
    """返回所有注册的用户名列表"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("SELECT username FROM lock_users")
            rows = cur.fetchall()
            return [r[0] for r in rows]
        else:
            stmt = conn.prepare("SELECT username FROM lock_users")
            rows = stmt()
            return [r[0] for r in rows]
    finally:
        conn.close()


def delete_lock_user(username):
    """删除指定用户"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("DELETE FROM lock_users WHERE username = ?", (username,))
            conn.commit()
            return cur.rowcount > 0
        else:
            stmt = conn.prepare("DELETE FROM lock_users WHERE username = $1")
            stmt(username)
            return True
    finally:
        conn.close()


def verify_user_credentials(username, password, pincode):
    """验证用户凭据：用户名 + 密码（用户各自）且 PINCODE 必须与全局 PIN 一致

    说明：根据新需求，PINCODE 为全局一致值（配置为 GLOBAL_PINCODE）。
    验证步骤：1) 检查用户名与密码是否匹配；2) 检查提供的 pincode 与全局 PIN 相同。
    """
    import hashlib
    from config import GLOBAL_PINCODE

    if str(pincode) != str(GLOBAL_PINCODE):
        return False

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM lock_users WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            )
            return cur.fetchone() is not None
        else:
            stmt = conn.prepare(
                "SELECT id FROM lock_users WHERE username = $1 AND password_hash = $2"
            )
            rows = stmt(username, password_hash)
            for _ in rows:
                return True
            return False
    finally:
        conn.close()


def get_user_face_image(username):
    """获取用户面部图像路径"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT face_image_path FROM lock_users WHERE username = ?",
                (username,)
            )
            row = cur.fetchone()
            return row[0] if row else None
        else:
            stmt = conn.prepare(
                "SELECT face_image_path FROM lock_users WHERE username = $1"
            )
            rows = stmt(username)
            for row in rows:
                return row[0]
            return None
    finally:
        conn.close()


def get_user_fingerprint_data(username):
    """获取用户指纹数据"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT fingerprint_data FROM lock_users WHERE username = ?",
                (username,)
            )
            row = cur.fetchone()
            return row[0] if row else None
        else:
            stmt = conn.prepare(
                "SELECT fingerprint_data FROM lock_users WHERE username = $1"
            )
            rows = stmt(username)
            for row in rows:
                return row[0]
            return None
    finally:
        conn.close()


def get_auto_lock_config(lock_id):
    """获取自动锁定配置"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT auto_lock_enabled, auto_lock_delay FROM lock_auto_config WHERE lock_id = ?",
                (lock_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    'auto_lock_enabled': bool(row[0]),
                    'auto_lock_delay': row[1]
                }
            return {'auto_lock_enabled': True, 'auto_lock_delay': 5}  # 默认值
        else:
            stmt = conn.prepare(
                "SELECT auto_lock_enabled, auto_lock_delay FROM lock_auto_config WHERE lock_id = $1"
            )
            rows = stmt(lock_id)
            for row in rows:
                return {
                    'auto_lock_enabled': bool(row[0]),
                    'auto_lock_delay': row[1]
                }
            return {'auto_lock_enabled': True, 'auto_lock_delay': 5}  # 默认值
    finally:
        conn.close()


def update_auto_lock_config(lock_id, auto_lock_enabled=True, auto_lock_delay=5):
    """更新自动锁定配置"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            # 检查是否存在
            cur.execute("SELECT lock_id FROM lock_auto_config WHERE lock_id = ?", (lock_id,))
            exists = cur.fetchone()
            
            if exists:
                cur.execute(
                    "UPDATE lock_auto_config SET auto_lock_enabled = ?, auto_lock_delay = ?, updated_at = CURRENT_TIMESTAMP WHERE lock_id = ?",
                    (1 if auto_lock_enabled else 0, auto_lock_delay, lock_id)
                )
            else:
                cur.execute(
                    "INSERT INTO lock_auto_config (lock_id, auto_lock_enabled, auto_lock_delay) VALUES (?, ?, ?)",
                    (lock_id, 1 if auto_lock_enabled else 0, auto_lock_delay)
                )
            conn.commit()
        else:
            # openGauss 处理
            stmt_check = conn.prepare("SELECT lock_id FROM lock_auto_config WHERE lock_id = $1")
            rows = stmt_check(lock_id)
            exists = False
            for _ in rows:
                exists = True
                break
            
            if exists:
                stmt = conn.prepare("""
                    UPDATE lock_auto_config 
                    SET auto_lock_enabled = $2, auto_lock_delay = $3, updated_at = NOW()
                    WHERE lock_id = $1
                """)
                stmt(lock_id, auto_lock_enabled, auto_lock_delay)
            else:
                stmt = conn.prepare("""
                    INSERT INTO lock_auto_config (lock_id, auto_lock_enabled, auto_lock_delay, updated_at)
                    VALUES ($1, $2, $3, NOW())
                """)
                stmt(lock_id, auto_lock_enabled, auto_lock_delay)
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

# ==================== 灯具控制数据库操作 ====================

def upsert_lighting_state(light_id, device_id=None, power=None, brightness=None, 
                         auto_mode=None, room_brightness=None, color_temp=None):
    """更新或插入灯具状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            # 检查是否存在
            cur.execute("SELECT 1 FROM lighting_state WHERE light_id = ?", (light_id,))
            exists = cur.fetchone()
            
            if exists:
                # 更新现有记录
                updates = []
                params = []
                if device_id is not None:
                    updates.append("device_id = ?")
                    params.append(device_id)
                if power is not None:
                    updates.append("power = ?")
                    params.append(power)
                if brightness is not None:
                    updates.append("brightness = ?")
                    params.append(brightness)
                if auto_mode is not None:
                    updates.append("auto_mode = ?")
                    params.append(auto_mode)
                if room_brightness is not None:
                    updates.append("room_brightness = ?")
                    params.append(room_brightness)
                if color_temp is not None:
                    updates.append("color_temp = ?")
                    params.append(color_temp)
                
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    params.append(light_id)
                    cur.execute(f"UPDATE lighting_state SET {', '.join(updates)} WHERE light_id = ?", params)
            else:
                # 插入新记录
                cur.execute("""
                    INSERT INTO lighting_state (light_id, device_id, power, brightness, auto_mode, room_brightness, color_temp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (light_id, device_id or 'room1', power or False, brightness or 50, 
                      auto_mode or False, room_brightness, color_temp or 4000))
            conn.commit()
        else:
            # openGauss 处理
            stmt_check = conn.prepare("SELECT light_id FROM lighting_state WHERE light_id = $1")
            rows = stmt_check(light_id)
            exists = False
            for _ in rows:
                exists = True
                break

            if exists:
                # 更新
                updates = []
                values = [light_id]  # WHERE light_id = $1
                param_count = 2

                if device_id is not None:
                    updates.append(f"device_id = ${param_count}")
                    values.append(device_id)
                    param_count += 1
                if power is not None:
                    updates.append(f"power = ${param_count}")
                    values.append(power)
                    param_count += 1
                if brightness is not None:
                    updates.append(f"brightness = ${param_count}")
                    values.append(brightness)
                    param_count += 1
                if auto_mode is not None:
                    updates.append(f"auto_mode = ${param_count}")
                    values.append(auto_mode)
                    param_count += 1
                if room_brightness is not None:
                    updates.append(f"room_brightness = ${param_count}")
                    values.append(room_brightness)
                    param_count += 1
                if color_temp is not None:
                    updates.append(f"color_temp = ${param_count}")
                    values.append(color_temp)
                    param_count += 1

                if updates:
                    updates.append("updated_at = NOW()")
                    sql = f"UPDATE lighting_state SET {', '.join(updates)} WHERE light_id = $1"
                    stmt = conn.prepare(sql)
                    stmt(*values)
            else:
                # 插入
                stmt = conn.prepare("""
                    INSERT INTO lighting_state
                    (light_id, device_id, power, brightness, auto_mode, room_brightness, color_temp, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """)
                stmt(light_id, device_id or 'room1', power or False, brightness or 50,
                     auto_mode or False, room_brightness, color_temp or 4000)
    finally:
        conn.close()


def get_lighting_state(light_id):
    """获取灯具状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                SELECT light_id, device_id, power, brightness, auto_mode, room_brightness, color_temp, updated_at
                FROM lighting_state WHERE light_id = ?
            """, (light_id,))
            row = cur.fetchone()
            if row:
                return {
                    'light_id': row[0],
                    'device_id': row[1],
                    'power': bool(row[2]),
                    'brightness': row[3],
                    'auto_mode': bool(row[4]),
                    'room_brightness': row[5],
                    'color_temp': row[6],
                    'updated_at': row[7]
                }
            return None
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                SELECT light_id, device_id, power, brightness, auto_mode, room_brightness, color_temp, updated_at
                FROM lighting_state WHERE light_id = $1
            """)
            rows = stmt(light_id)
            for row in rows:
                return {
                    'light_id': row[0],
                    'device_id': row[1],
                    'power': bool(row[2]),
                    'brightness': row[3],
                    'auto_mode': bool(row[4]),
                    'room_brightness': row[5],
                    'color_temp': row[6],
                    'updated_at': row[7].isoformat() if row[7] else None
                }
            return None
    finally:
        conn.close()


def get_all_lights():
    """获取所有灯具状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                SELECT light_id, device_id, power, brightness, auto_mode, room_brightness, color_temp, updated_at
                FROM lighting_state
            """)
            rows = cur.fetchall()
            return [
                {
                    'light_id': r[0],
                    'device_id': r[1],
                    'power': bool(r[2]),
                    'brightness': r[3],
                    'auto_mode': bool(r[4]),
                    'room_brightness': r[5],
                    'color_temp': r[6],
                    'updated_at': r[7]
                } for r in rows
            ]
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                SELECT light_id, device_id, power, brightness, auto_mode, room_brightness, color_temp, updated_at
                FROM lighting_state
            """)
            rows = stmt()
            result = []
            for r in rows:
                result.append({
                    'light_id': r[0],
                    'device_id': r[1],
                    'power': bool(r[2]),
                    'brightness': r[3],
                    'auto_mode': bool(r[4]),
                    'room_brightness': r[5],
                    'color_temp': r[6],
                    'updated_at': r[7].isoformat() if r[7] else None
                })
            return result
    finally:
        conn.close()


def insert_lighting_event(light_id, event_type, old_value=None, new_value=None, detail=None):
    """记录灯具事件"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO lighting_events (light_id, event_type, old_value, new_value, detail)
                VALUES (?, ?, ?, ?, ?)
            """, (light_id, event_type, old_value, new_value, detail))
            conn.commit()
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                INSERT INTO lighting_events (light_id, event_type, old_value, new_value, detail, timestamp)
                VALUES ($1, $2, $3, $4, $5, NOW())
            """)
            stmt(light_id, event_type, old_value, new_value, detail)
    finally:
        conn.close()


def get_lighting_events(light_id, limit=50):
    """获取灯具事件历史"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                SELECT id, light_id, event_type, old_value, new_value, detail, timestamp
                FROM lighting_events WHERE light_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (light_id, limit))
            rows = cur.fetchall()
            return [
                {
                    'id': r[0],
                    'light_id': r[1],
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
                SELECT id, light_id, event_type, old_value, new_value, detail, timestamp
                FROM lighting_events WHERE light_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """)
            rows = stmt(light_id, limit)
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'light_id': r[1],
                    'event_type': r[2],
                    'old_value': r[3],
                    'new_value': r[4],
                    'detail': r[5],
                    'timestamp': r[6].isoformat() if r[6] else None
                })
            return result
    finally:
        conn.close()
# ==================== 烟雾报警器功能 ====================

def upsert_smoke_alarm_state(alarm_id, location=None, smoke_level=None, alarm_active=None,
                              battery=None, test_mode=None, sensitivity=None):
    """更新或插入烟雾报警器状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            # 检查是否存在
            cur.execute("SELECT alarm_id FROM smoke_alarm_state WHERE alarm_id = ?", (alarm_id,))
            exists = cur.fetchone()

            if exists:
                # 更新
                updates = []
                values = []
                if location is not None:
                    updates.append("location = ?")
                    values.append(location)
                if smoke_level is not None:
                    updates.append("smoke_level = ?")
                    values.append(smoke_level)
                if alarm_active is not None:
                    updates.append("alarm_active = ?")
                    values.append(1 if alarm_active else 0)
                if battery is not None:
                    updates.append("battery = ?")
                    values.append(battery)
                if test_mode is not None:
                    updates.append("test_mode = ?")
                    values.append(1 if test_mode else 0)
                if sensitivity is not None:
                    updates.append("sensitivity = ?")
                    values.append(sensitivity)

                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    values.append(alarm_id)
                    sql = f"UPDATE smoke_alarm_state SET {', '.join(updates)} WHERE alarm_id = ?"
                    cur.execute(sql, values)
            else:
                # 插入
                cur.execute(
                    """INSERT INTO smoke_alarm_state
                       (alarm_id, location, smoke_level, alarm_active, battery, test_mode, sensitivity)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (alarm_id, location or 'unknown',
                     smoke_level or 0.0,
                     1 if alarm_active else 0,
                     battery or 100,
                     1 if test_mode else 0,
                     sensitivity or 'medium')
                )
            conn.commit()
        else:
            # openGauss 处理
            stmt_check = conn.prepare("SELECT alarm_id FROM smoke_alarm_state WHERE alarm_id = $1")
            rows = stmt_check(alarm_id)
            exists = False
            for _ in rows:
                exists = True
                break

            if exists:
                # 更新
                updates = []
                values = [alarm_id]  # WHERE alarm_id = $1
                param_count = 2

                if location is not None:
                    updates.append(f"location = ${param_count}")
                    values.append(location)
                    param_count += 1
                if smoke_level is not None:
                    updates.append(f"smoke_level = ${param_count}")
                    values.append(smoke_level)
                    param_count += 1
                if alarm_active is not None:
                    updates.append(f"alarm_active = ${param_count}")
                    values.append(alarm_active)
                    param_count += 1
                if battery is not None:
                    updates.append(f"battery = ${param_count}")
                    values.append(battery)
                    param_count += 1
                if test_mode is not None:
                    updates.append(f"test_mode = ${param_count}")
                    values.append(test_mode)
                    param_count += 1
                if sensitivity is not None:
                    updates.append(f"sensitivity = ${param_count}")
                    values.append(sensitivity)
                    param_count += 1

                if updates:
                    updates.append("updated_at = NOW()")
                    sql = f"UPDATE smoke_alarm_state SET {', '.join(updates)} WHERE alarm_id = $1"
                    stmt = conn.prepare(sql)
                    stmt(*values)
            else:
                # 插入
                stmt = conn.prepare("""
                    INSERT INTO smoke_alarm_state
                    (alarm_id, location, smoke_level, alarm_active, battery, test_mode, sensitivity, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """)
                stmt(alarm_id, location or 'unknown', smoke_level or 0.0,
                     alarm_active or False, battery or 100, test_mode or False, sensitivity or 'medium')
    finally:
        conn.close()


def get_smoke_alarm_state(alarm_id):
    """获取烟雾报警器状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """SELECT alarm_id, location, smoke_level, alarm_active, battery,
                          test_mode, sensitivity, updated_at
                   FROM smoke_alarm_state WHERE alarm_id = ?""",
                (alarm_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    'alarm_id': row[0],
                    'location': row[1],
                    'smoke_level': row[2],
                    'alarm_active': bool(row[3]),
                    'battery': row[4],
                    'test_mode': bool(row[5]),
                    'sensitivity': row[6],
                    'updated_at': row[7]
                }
            return None
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                SELECT alarm_id, location, smoke_level, alarm_active, battery,
                       test_mode, sensitivity, updated_at
                FROM smoke_alarm_state WHERE alarm_id = $1
            """)
            rows = stmt(alarm_id)
            for row in rows:
                return {
                    'alarm_id': row[0],
                    'location': row[1],
                    'smoke_level': row[2],
                    'alarm_active': bool(row[3]),
                    'battery': row[4],
                    'test_mode': bool(row[5]),
                    'sensitivity': row[6],
                    'updated_at': row[7].isoformat() if row[7] else None
                }
            return None
    finally:
        conn.close()


def get_all_smoke_alarms():
    """获取所有烟雾报警器状态"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """SELECT alarm_id, location, smoke_level, alarm_active, battery,
                          test_mode, sensitivity, updated_at
                   FROM smoke_alarm_state"""
            )
            rows = cur.fetchall()
            return [
                {
                    'alarm_id': r[0],
                    'location': r[1],
                    'smoke_level': r[2],
                    'alarm_active': bool(r[3]),
                    'battery': r[4],
                    'test_mode': bool(r[5]),
                    'sensitivity': r[6],
                    'updated_at': r[7]
                } for r in rows
            ]
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                SELECT alarm_id, location, smoke_level, alarm_active, battery,
                       test_mode, sensitivity, updated_at
                FROM smoke_alarm_state
            """)
            rows = stmt()
            result = []
            for r in rows:
                result.append({
                    'alarm_id': r[0],
                    'location': r[1],
                    'smoke_level': r[2],
                    'alarm_active': bool(r[3]),
                    'battery': r[4],
                    'test_mode': bool(r[5]),
                    'sensitivity': r[6],
                    'updated_at': r[7].isoformat() if r[7] else None
                })
            return result
    finally:
        conn.close()


def insert_smoke_alarm_event(alarm_id, event_type, smoke_level=None, detail=None):
    """记录烟雾报警器事件"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO smoke_alarm_events (alarm_id, event_type, smoke_level, detail)
                   VALUES (?, ?, ?, ?)""",
                (alarm_id, event_type, smoke_level, detail)
            )
            conn.commit()
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                INSERT INTO smoke_alarm_events (alarm_id, event_type, smoke_level, detail, timestamp)
                VALUES ($1, $2, $3, $4, NOW())
            """)
            stmt(alarm_id, event_type, smoke_level, detail)
    finally:
        conn.close()


def get_smoke_alarm_events(alarm_id, limit=50):
    """获取烟雾报警器事件历史"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                """SELECT id, alarm_id, event_type, smoke_level, detail, timestamp
                   FROM smoke_alarm_events WHERE alarm_id = ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (alarm_id, limit)
            )
            rows = cur.fetchall()
            return [
                {
                    'id': r[0],
                    'alarm_id': r[1],
                    'event_type': r[2],
                    'smoke_level': r[3],
                    'detail': r[4],
                    'timestamp': r[5]
                } for r in rows
            ]
        else:
            # openGauss 处理
            stmt = conn.prepare("""
                SELECT id, alarm_id, event_type, smoke_level, detail, timestamp
                FROM smoke_alarm_events WHERE alarm_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """)
            rows = stmt(alarm_id, limit)
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'alarm_id': r[1],
                    'event_type': r[2],
                    'smoke_level': r[3],
                    'detail': r[4],
                    'timestamp': r[5].isoformat() if r[5] else None
                })
            return result
    finally:
        conn.close()


