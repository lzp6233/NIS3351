"""
传感器模拟器
模拟多个温湿度传感器设备
"""

import time
import random
import json
import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, INTERVAL, SENSORS


def generate_sensor_data():
    """生成模拟的温湿度数据"""
    temperature = round(random.uniform(20, 30), 1)
    humidity = round(random.uniform(40, 60), 1)
    return {"temperature": temperature, "humidity": humidity}


def main():
    # 创建 MQTT 客户端
    client = mqtt.Client()
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("="*60)
        print("温湿度传感器模拟器已启动")
        print("="*60)
        
        # 显示要模拟的设备
        enabled_sensors = [s for s in SENSORS if s.get('enabled', True)]
        print(f"\n模拟设备数量: {len(enabled_sensors)}")
        for sensor in enabled_sensors:
            print(f"  - {sensor['location']} ({sensor['device_id']})")
            print(f"    主题: {sensor['topic']}")
        
        print(f"\n发送间隔: {INTERVAL} 秒")
        print("="*60)
        print()
        
        while True:
            # 为每个启用的传感器生成并发送数据
            for sensor in enabled_sensors:
                if not sensor.get('enabled', True):
                    continue
                
                data = generate_sensor_data()
                topic = sensor['topic']
                
                # 发送数据
                client.publish(topic, json.dumps(data))
                
                # 打印日志
                print(f"📤 [{sensor['device_id']}] {sensor['location']}: "
                      f"温度 {data['temperature']}°C, 湿度 {data['humidity']}%")
            
            time.sleep(INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n停止模拟器...")
        client.disconnect()
        print("✓ 已停止")
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        print("请确保 MQTT Broker 正在运行")


if __name__ == "__main__":
    main()
