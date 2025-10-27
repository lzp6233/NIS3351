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
    根据空调的运行模式智能调节温湿度：
    - cool (制冷): 降温 + 除湿
    - heat (制热): 升温 + 干燥
    - fan (送风): 微小波动，不主动调节
    - dehumidify (除湿): 轻微降温 + 强力除湿
    """
    # 初始化设备温度状态（从数据库读取最后值，避免重启时跳变）
    if device_id not in device_current_temps:
        # 尝试从数据库获取最后一次的温湿度值
        from database import get_latest_data
        latest_data = get_latest_data(device_id)
        
        if latest_data:
            # 使用数据库中的最后值作为初始值
            device_current_temps[device_id] = latest_data['temperature']
            print(f"📊 [{device_id}] 从数据库恢复温度: {latest_data['temperature']}°C")
        else:
            # 如果数据库中没有数据，使用随机值
            device_current_temps[device_id] = round(random.uniform(24, 28), 1)
            print(f"📊 [{device_id}] 初始化温度: {device_current_temps[device_id]}°C")
    
    # 初始化湿度状态（从数据库读取最后值，避免重启时跳变）
    if not hasattr(generate_sensor_data, 'device_current_humidity'):
        generate_sensor_data.device_current_humidity = {}
    
    if device_id not in generate_sensor_data.device_current_humidity:
        # 尝试从数据库获取最后一次的湿度值
        from database import get_latest_data
        latest_data = get_latest_data(device_id)
        
        if latest_data:
            # 使用数据库中的最后值作为初始值
            generate_sensor_data.device_current_humidity[device_id] = latest_data['humidity']
            print(f"💧 [{device_id}] 从数据库恢复湿度: {latest_data['humidity']}%")
        else:
            # 如果数据库中没有数据，使用随机值
            generate_sensor_data.device_current_humidity[device_id] = round(random.uniform(50, 60), 1)
            print(f"💧 [{device_id}] 初始化湿度: {generate_sensor_data.device_current_humidity[device_id]}%")
    
    current_temp = device_current_temps[device_id]
    current_humidity = generate_sensor_data.device_current_humidity[device_id]
    
    # 检查该房间是否有空调在运行
    ac_id = f"ac_{device_id}"
    ac_state = get_ac_state(ac_id)
    
    if ac_state and ac_state.get('power'):
        # 空调开启，根据模式调整温湿度
        mode = ac_state.get('mode', 'cool')
        target_temp = ac_state.get('target_temp', 26.0)
        
        if mode == 'cool':
            # 制冷模式：降温 + 除湿
            temp_change = random.uniform(0.3, 0.8)
            
            if current_temp > target_temp:
                new_temp = current_temp - temp_change
                new_temp = max(new_temp, target_temp)
            elif current_temp < target_temp:
                new_temp = current_temp + temp_change * 0.3  # 制冷模式下升温很慢
                new_temp = min(new_temp, target_temp)
            else:
                new_temp = target_temp + random.uniform(-0.2, 0.2)
            
            # 制冷除湿：湿度根据当前值动态调整
            # 湿度越高，除湿效果越明显；湿度低时，除湿减缓，甚至微微回升
            if current_humidity > 55:
                humidity_change = random.uniform(0.8, 2.0)  # 高湿度时除湿快
            elif current_humidity > 45:
                humidity_change = random.uniform(0.3, 1.0)  # 中等湿度
            elif current_humidity > 38:
                humidity_change = random.uniform(0.05, 0.3)  # 低湿度时除湿很慢
            else:
                # 湿度过低时，自然回升（空气中的水分渗透）
                humidity_change = random.uniform(-0.3, 0.1)  # 可能微微回升
            
            new_humidity = current_humidity - humidity_change
            new_humidity = max(35, min(70, new_humidity))  # 35-70% 范围
            
        elif mode == 'heat':
            # 制热模式：升温 + 干燥
            temp_change = random.uniform(0.4, 0.9)  # 制热稍快
            
            if current_temp < target_temp:
                new_temp = current_temp + temp_change
                new_temp = min(new_temp, target_temp)
            elif current_temp > target_temp:
                new_temp = current_temp - temp_change * 0.3  # 制热模式下降温很慢
                new_temp = max(new_temp, target_temp)
            else:
                new_temp = target_temp + random.uniform(-0.2, 0.2)
            
            # 制热干燥：湿度根据当前值动态调整
            if current_humidity > 55:
                humidity_change = random.uniform(0.5, 1.2)  # 高湿度时干燥明显
            elif current_humidity > 45:
                humidity_change = random.uniform(0.2, 0.8)  # 中等湿度
            elif current_humidity > 35:
                humidity_change = random.uniform(0.05, 0.4)  # 低湿度时干燥慢
            else:
                # 湿度过低时，自然回升
                humidity_change = random.uniform(-0.2, 0.15)  # 可能微微回升
            
            new_humidity = current_humidity - humidity_change
            new_humidity = max(30, min(70, new_humidity))  # 30-70% 范围
            
        elif mode == 'fan':
            # 送风模式：几乎不调节温湿度，只有微小波动
            # 但会让湿度逐渐向环境湿度回归
            new_temp = current_temp + random.uniform(-0.1, 0.1)
            
            # 湿度向环境湿度（55%）缓慢回归
            ambient_humidity = 55.0
            humidity_drift = (ambient_humidity - current_humidity) * 0.05  # 5%速度回归
            new_humidity = current_humidity + humidity_drift + random.uniform(-0.3, 0.3)
            
        elif mode == 'dehumidify':
            # 除湿模式：轻微降温 + 强力除湿
            temp_change = random.uniform(0.1, 0.3)  # 除湿时温度稍微下降
            
            # 轻微降温
            new_temp = current_temp - temp_change
            new_temp = max(new_temp, target_temp - 2)  # 除湿模式不会降温太多
            
            # 强力除湿：湿度越高，除湿越快
            if current_humidity > 60:
                humidity_change = random.uniform(2.0, 4.0)  # 高湿度强力除湿
            elif current_humidity > 50:
                humidity_change = random.uniform(1.0, 2.5)  # 中高湿度
            elif current_humidity > 40:
                humidity_change = random.uniform(0.5, 1.5)  # 中等湿度
            else:
                humidity_change = random.uniform(0.1, 0.6)  # 低湿度时除湿变慢
            
            new_humidity = current_humidity - humidity_change
            new_humidity = max(30, min(70, new_humidity))  # 30-70% 范围
            
        else:
            # 未知模式，使用默认制冷逻辑
            temp_change = random.uniform(0.3, 0.8)
            if current_temp > target_temp:
                new_temp = current_temp - temp_change
                new_temp = max(new_temp, target_temp)
            else:
                new_temp = target_temp + random.uniform(-0.2, 0.2)
            new_humidity = current_humidity - random.uniform(0.5, 1.5)
        
        device_current_temps[device_id] = round(new_temp, 1)
        generate_sensor_data.device_current_humidity[device_id] = round(new_humidity, 1)
        
    else:
        # 空调关闭或不存在，温湿度自然波动
        # 温度逐渐趋向环境温度 (假设环境温度 27°C)
        ambient_temp = 27.0
        ambient_humidity = 55.0
        
        # 温度向环境温度漂移
        temp_drift = (ambient_temp - current_temp) * 0.1
        natural_temp_variation = random.uniform(-0.3, 0.3)
        new_temp = current_temp + temp_drift + natural_temp_variation
        
        # 湿度向环境湿度漂移
        humidity_drift = (ambient_humidity - current_humidity) * 0.1
        natural_humidity_variation = random.uniform(-2, 2)
        new_humidity = current_humidity + humidity_drift + natural_humidity_variation
        
        device_current_temps[device_id] = round(new_temp, 1)
        generate_sensor_data.device_current_humidity[device_id] = round(new_humidity, 1)
    
    # 确保温湿度在合理范围内
    final_temp = max(10, min(40, device_current_temps[device_id]))
    final_humidity = max(20, min(80, generate_sensor_data.device_current_humidity[device_id]))
    
    return {
        "temperature": final_temp,
        "humidity": final_humidity
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
                    mode = ac_state.get('mode', 'cool')
                    mode_icons = {
                        'cool': '❄️',
                        'heat': '🔥',
                        'fan': '💨',
                        'dehumidify': '💧'
                    }
                    mode_icon = mode_icons.get(mode, '🌡️')
                    ac_status = f" [空调: {mode_icon} {mode.upper()}, 目标 {target}°C]"
                
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
