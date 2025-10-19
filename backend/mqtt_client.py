"""
MQTT 客户端模块
订阅温湿度传感器主题，支持多个设备
"""

import paho.mqtt.client as mqtt
import json
from database import insert_sensor_data
from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC


def parse_device_id(topic):
    """
    从主题中提取设备ID
    例如: home/room1/temperature_humidity -> room1
          home/room2/temperature_humidity -> room2
    """
    parts = topic.split('/')
    if len(parts) >= 2:
        return parts[1]  # 返回位置作为设备ID
    return 'room1'  # 默认


def on_connect(client, userdata, flags, rc):
    """连接回调"""
    if rc == 0:
        print(f"✓ 已连接到 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"✓ 已订阅主题: {MQTT_TOPIC}")
    else:
        print(f"✗ 连接失败，返回码: {rc}")


def on_message(client, userdata, msg):
    """
    消息回调：处理温湿度数据
    """
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        
        # 解析设备ID
        device_id = parse_device_id(topic)
        
        # 解析数据
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            # 兼容旧格式：字符串字典
            data = eval(payload)
        
        # 插入数据库
        insert_sensor_data(data, device_id)
        
        # 打印日志
        print(f"📨 [{device_id}] 温度: {data['temperature']}°C, 湿度: {data['humidity']}%")
        
    except Exception as e:
        print(f"✗ 处理消息时出错: {e}")
        print(f"  主题: {msg.topic}")
        print(f"  数据: {msg.payload.decode()}")


def on_disconnect(client, userdata, rc):
    """断开连接回调"""
    if rc != 0:
        print(f"⚠ 意外断开连接，返回码: {rc}")


# 创建 MQTT 客户端
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

# 连接到 MQTT Broker
try:
    print(f"正在连接到 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    print("✓ MQTT 客户端已启动")
except Exception as e:
    print(f"✗ 连接 MQTT Broker 失败: {e}")
    print("  请确保 MQTT Broker (EMQX/Mosquitto) 正在运行")


if __name__ == "__main__":
    print("="*50)
    print("MQTT 客户端运行中...")
    print(f"订阅主题: {MQTT_TOPIC}")
    print("="*50)
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止 MQTT 客户端...")
        client.loop_stop()
        client.disconnect()
        print("✓ 已停止")
