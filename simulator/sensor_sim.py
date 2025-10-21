"""
传感器模拟器
模拟多个温湿度传感器设备
根据空调状态智能调整温度生成
"""

import time
import random
import json
import sys
import os
import paho.mqtt.client as mqtt

# 添加 backend 路径
current_dir = os.path.dirname(__file__)
backend_dir = os.path.join(current_dir, '..', 'backend')
sys.path.insert(0, backend_dir)

# 从统一的配置文件导入
from config import MQTT_BROKER, MQTT_PORT, INTERVAL, SENSORS
from database import get_ac_state


# 每个设备的当前温度状态（模拟真实物理环境）
device_current_temps = {}


def generate_sensor_data(device_id):
    """
    生成模拟的温湿度数据
    如果有空调在运行，温度会逐渐向目标温度靠近
    """
    # 初始化设备温度
    if device_id not in device_current_temps:
        device_current_temps[device_id] = round(random.uniform(24, 28), 1)
    
    current_temp = device_current_temps[device_id]
    
    # 检查该房间是否有空调在运行
    ac_id = f"ac_{device_id}"
    ac_state = get_ac_state(ac_id)
    
    if ac_state and ac_state.get('power'):
        # 空调开启，温度向目标温度调整
        target_temp = ac_state.get('target_temp', 26.0)
        
        # 温度变化速度（每次调整 0.3-0.8 度）
        temp_change = random.uniform(0.3, 0.8)
        
        if current_temp > target_temp:
            # 当前温度高于目标，降温
            new_temp = current_temp - temp_change
            new_temp = max(new_temp, target_temp)  # 不低于目标温度
        elif current_temp < target_temp:
            # 当前温度低于目标，升温
            new_temp = current_temp + temp_change
            new_temp = min(new_temp, target_temp)  # 不高于目标温度
        else:
            # 已达到目标温度，保持稳定（微小波动）
            new_temp = target_temp + random.uniform(-0.2, 0.2)
        
        device_current_temps[device_id] = round(new_temp, 1)
    else:
        # 空调关闭或不存在，温度自然波动
        # 温度逐渐趋向环境温度 (假设环境温度 26-28°C)
        ambient_temp = 27.0
        drift = (ambient_temp - current_temp) * 0.1  # 10% 向环境温度漂移
        natural_variation = random.uniform(-0.3, 0.3)
        new_temp = current_temp + drift + natural_variation
        device_current_temps[device_id] = round(new_temp, 1)
    
    # 湿度生成（受温度影响，温度低时湿度略高）
    base_humidity = 50
    temp_factor = (25 - device_current_temps[device_id]) * 2  # 温度每低1度，湿度+2%
    humidity = round(base_humidity + temp_factor + random.uniform(-5, 5), 1)
    humidity = max(30, min(70, humidity))  # 限制在 30-70%
    
    return {
        "temperature": device_current_temps[device_id],
        "humidity": humidity
    }


def main():
    # 创建 MQTT 客户端
    client = mqtt.Client()
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("="*60)
        print("温湿度传感器模拟器已启动（智能空调感知）")
        print("="*60)
        
        # 显示要模拟的设备
        enabled_sensors = [s for s in SENSORS if s.get('enabled', True)]
        print(f"\n模拟设备数量: {len(enabled_sensors)}")
        for sensor in enabled_sensors:
            print(f"  - {sensor['location']} ({sensor['device_id']})")
            print(f"    主题: {sensor['topic']}")
        
        print(f"\n发送间隔: {INTERVAL} 秒")
        print("\n💡 特性: 温度会根据空调状态智能调整")
        print("   - 空调开启时: 温度逐渐向目标温度靠近")
        print("   - 空调关闭时: 温度自然波动")
        print("="*60)
        print()
        
        while True:
            # 为每个启用的传感器生成并发送数据
            for sensor in enabled_sensors:
                if not sensor.get('enabled', True):
                    continue
                
                device_id = sensor['device_id']
                data = generate_sensor_data(device_id)
                topic = sensor['topic']
                
                # 检查空调状态以显示更详细的日志
                ac_id = f"ac_{device_id}"
                ac_state = get_ac_state(ac_id)
                ac_status = ""
                if ac_state and ac_state.get('power'):
                    target = ac_state.get('target_temp')
                    ac_status = f" [空调: ON, 目标 {target}°C]"
                
                # 发送数据
                client.publish(topic, json.dumps(data))
                
                # 打印日志
                print(f"📤 [{device_id}] {sensor['location']}: "
                      f"温度 {data['temperature']}°C, 湿度 {data['humidity']}%{ac_status}")
            
            time.sleep(INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n停止模拟器...")
        client.disconnect()
        print("✓ 已停止")
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        print("请确保 MQTT Broker 正在运行")


if __name__ == "__main__":
    main()
