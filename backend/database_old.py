"""
数据库操作模块
提供温湿度传感器数据管理接口，支持多个设备
"""

import psycopg2
from config import DB_CONFIG


def get_connection():
    """获取数据库连接"""
    conn = psycopg2.connect(
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"]
    )
    return conn


def insert_sensor_data(data, device_id='room1'):
    """
    插入温湿度传感器数据
    
    Args:
        data: 包含 temperature 和 humidity 的字典
        device_id: 设备标识（如：room1, room2）
    """
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
    """
    获取最近的温湿度数据
    
    Args:
        device_id: 设备标识（可选，不指定则返回所有设备）
        limit: 返回记录数量
    """
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
