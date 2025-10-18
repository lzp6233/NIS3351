"""
数据库操作模块（使用 psycopg3）
支持 GaussDB 的 SCRAM-SHA-256 认证
"""

import psycopg
from config import DB_CONFIG


def get_connection():
    """
    获取数据库连接
    使用 psycopg3，原生支持 SCRAM-SHA-256
    """
    conn_string = f"dbname={DB_CONFIG['dbname']} user={DB_CONFIG['user']} password={DB_CONFIG['password']} host={DB_CONFIG['host']} port={DB_CONFIG['port']}"
    conn = psycopg.connect(conn_string)
    return conn


def insert_sensor_data(data, device_id='room1'):
    """插入温湿度传感器数据"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO temperature_humidity_data (device_id, temperature, humidity) VALUES (%s, %s, %s)",
            (device_id, data["temperature"], data["humidity"])
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_recent_data(device_id=None, limit=100):
    """获取最近的温湿度数据"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        if device_id:
            cur.execute("""
                SELECT id, device_id, temperature, humidity, timestamp 
                FROM temperature_humidity_data 
                WHERE device_id = %s
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (device_id, limit))
        else:
            cur.execute("""
                SELECT id, device_id, temperature, humidity, timestamp 
                FROM temperature_humidity_data 
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (limit,))
        
        rows = cur.fetchall()
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
        cur.close()
        conn.close()


def get_devices():
    """获取所有设备列表"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT device_id, COUNT(*) as count
            FROM temperature_humidity_data
            GROUP BY device_id
            ORDER BY device_id
        """)
        rows = cur.fetchall()
        return [{'device_id': row[0], 'data_count': row[1]} for row in rows]
    finally:
        cur.close()
        conn.close()


def get_latest_data(device_id):
    """获取指定设备的最新数据"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, device_id, temperature, humidity, timestamp 
            FROM temperature_humidity_data 
            WHERE device_id = %s
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (device_id,))
        
        row = cur.fetchone()
        if row:
            return {
                'id': row[0],
                'device_id': row[1],
                'temperature': row[2],
                'humidity': row[3],
                'timestamp': row[4].isoformat() if row[4] else None
            }
        return None
    finally:
        cur.close()
        conn.close()

