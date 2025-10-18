"""
传感器模拟器配置
"""

# MQTT 配置
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883

# 发送间隔（秒）
INTERVAL = 5

# 要模拟的温湿度传感器设备列表
# 可以添加更多设备，支持扩展
SENSORS = [
    {
        "device_id": "room1",
        "location": "客厅",
        "topic": "home/room1/temperature_humidity",
        "enabled": True
    },
    {
        "device_id": "room2",
        "location": "卧室",
        "topic": "home/room2/temperature_humidity",
        "enabled": True
    },
    # 后续可以添加更多传感器
    # {
    #     "device_id": "room3",
    #     "location": "厨房",
    #     "topic": "home/room3/temperature_humidity",
    #     "enabled": True
    # },
]
