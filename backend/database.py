"""
数据库操作模块（使用 py-opengauss）
支持 openGauss 的 SCRAM-SHA-256 认证
"""

import py_opengauss
from config import DB_CONFIG


def get_connection():
    """
    获取数据库连接
    使用 py-opengauss，openGauss 官方驱动
    """
    # 构建连接字符串: opengauss://user:password@host:port/database
    conn_string = f"opengauss://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    conn = py_opengauss.open(conn_string)
    return conn


def insert_sensor_data(data, device_id='room1'):
    """插入温湿度传感器数据"""
    conn = get_connection()
    try:
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
        
        result = []
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

