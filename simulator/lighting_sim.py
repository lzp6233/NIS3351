"""
灯具模拟器
模拟全屋灯具控制，包括智能调节模式
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import threading
from datetime import datetime

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# 灯具配置
LIGHTS = {
    "light_room1": {"device_id": "room1", "name": "卧室1"},
    "light_room2": {"device_id": "room2", "name": "卧室2"},
    "light_living": {"device_id": "living", "name": "客厅"},
    "light_kitchen": {"device_id": "kitchen", "name": "厨房"}
}

# 全局灯具状态
light_states = {}

# MQTT 客户端
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)


def init_light_states():
    """初始化灯具状态"""
    for light_id, config in LIGHTS.items():
        light_states[light_id] = {
            "power": False,
            "brightness": 50,
            "auto_mode": False,
            "room_brightness": random.uniform(20, 80),  # 模拟房间亮度
            "color_temp": 4000,
            "device_id": config["device_id"],
            "name": config["name"]
        }


def on_connect(client, userdata, flags, rc):
    """连接回调"""
    if rc == 0:
        print("✓ 灯具模拟器已连接到 MQTT Broker")
        # 订阅控制命令
        for light_id in LIGHTS.keys():
            client.subscribe(f"home/lighting/{light_id}/cmd")
            client.subscribe(f"home/lighting/{light_id}/auto_adjust")
        print("✓ 已订阅灯具控制主题")
    else:
        print(f"✗ 连接失败，返回码: {rc}")


def on_message(client, userdata, msg):
    """消息回调：处理控制命令"""
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        
        # 解析灯具ID
        parts = topic.split('/')
        light_id = parts[2]
        
        if light_id not in light_states:
            print(f"✗ 未知灯具ID: {light_id}")
            return
        
        if topic.endswith('/cmd'):
            # 处理控制命令
            handle_lighting_command(light_id, payload)
        elif topic.endswith('/auto_adjust'):
            # 处理智能调节命令
            handle_auto_adjust(light_id, payload)
            
    except Exception as e:
        print(f"✗ 处理消息时出错: {e}")


def handle_lighting_command(light_id, command):
    """处理灯具控制命令"""
    state = light_states[light_id]
    old_state = state.copy()
    
    # 更新状态
    if 'power' in command:
        state['power'] = command['power']
    if 'brightness' in command:
        state['brightness'] = max(0, min(100, command['brightness']))
    if 'auto_mode' in command:
        state['auto_mode'] = command['auto_mode']
    if 'color_temp' in command:
        state['color_temp'] = max(2700, min(6500, command['color_temp']))
    
    # 发布状态更新
    publish_lighting_state(light_id)
    
    # 记录事件
    events = []
    if old_state['power'] != state['power']:
        events.append(f"Power {'ON' if state['power'] else 'OFF'}")
    if old_state['brightness'] != state['brightness']:
        events.append(f"Brightness {old_state['brightness']}% → {state['brightness']}%")
    if old_state['auto_mode'] != state['auto_mode']:
        events.append(f"Auto mode {'ON' if state['auto_mode'] else 'OFF'}")
    if old_state['color_temp'] != state['color_temp']:
        events.append(f"Color temp {old_state['color_temp']}K → {state['color_temp']}K")
    
    if events:
        publish_lighting_event(light_id, "manual_control", "; ".join(events))
        print(f"📨 [{light_id}] 控制命令: {', '.join(events)}")


def handle_auto_adjust(light_id, command):
    """处理智能调节命令"""
    state = light_states[light_id]
    room_brightness = command.get('room_brightness', state['room_brightness'])
    
    # 更新房间亮度
    state['room_brightness'] = room_brightness
    
    # 统一的智能控制逻辑：基于30 lux阈值的开关控制
    if state['auto_mode']:
        brightness_threshold = 30  # lux
        old_power = state['power']
        
        if room_brightness < brightness_threshold:
            # 房间太暗，自动开灯
            if not old_power:
                state['power'] = True
                state['brightness'] = 70  # 默认亮度70%
                
                # 发布状态更新
                publish_lighting_state(light_id)
                
                # 记录事件
                publish_lighting_event(light_id, "auto_power_on", 
                                     f"Auto turned on due to low room brightness ({room_brightness} lux < {brightness_threshold} lux)")
                print(f"📨 [{light_id}] 智能调节: 房间亮度{room_brightness:.1f} lux < {brightness_threshold} lux，自动开灯")
        else:
            # 房间亮度足够，自动关灯
            if old_power:
                state['power'] = False
                
                # 发布状态更新
                publish_lighting_state(light_id)
                
                # 记录事件
                publish_lighting_event(light_id, "auto_power_off", 
                                     f"Auto turned off due to sufficient room brightness ({room_brightness} lux >= {brightness_threshold} lux)")
                print(f"📨 [{light_id}] 智能调节: 房间亮度{room_brightness:.1f} lux >= {brightness_threshold} lux，自动关灯")


def publish_lighting_state(light_id):
    """发布灯具状态"""
    state = light_states[light_id]
    topic = f"home/lighting/{light_id}/state"
    payload = {
        "power": state["power"],
        "brightness": state["brightness"],
        "auto_mode": state["auto_mode"],
        "room_brightness": state["room_brightness"],
        "color_temp": state["color_temp"],
        "timestamp": datetime.now().isoformat()
    }
    client.publish(topic, json.dumps(payload))


def publish_lighting_event(light_id, event_type, detail):
    """发布灯具事件"""
    topic = f"home/lighting/{light_id}/event"
    payload = {
        "type": event_type,
        "detail": detail,
        "timestamp": datetime.now().isoformat()
    }
    client.publish(topic, json.dumps(payload))


def simulate_room_brightness():
    """模拟房间亮度变化"""
    while True:
        try:
            for light_id, state in light_states.items():
                # 模拟房间亮度自然变化
                current_brightness = state['room_brightness']
                # 随机变化 ±5
                change = random.uniform(-5, 5)
                new_brightness = max(0, min(100, current_brightness + change))
                state['room_brightness'] = new_brightness
                
                # 如果智能模式开启，自动调节
                if state['auto_mode']:
                    handle_auto_adjust(light_id, {"room_brightness": new_brightness})
            
            time.sleep(30)  # 每30秒更新一次
        except Exception as e:
            print(f"✗ 模拟房间亮度时出错: {e}")
            time.sleep(5)


def main():
    """主函数"""
    print("="*60)
    print("💡 灯具模拟器启动")
    print("="*60)
    
    # 初始化灯具状态
    init_light_states()
    
    # 设置MQTT回调
    client.on_connect = on_connect
    client.on_message = on_message
    
    # 连接到MQTT Broker
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print("✓ MQTT 客户端已启动")
    except Exception as e:
        print(f"✗ 连接 MQTT Broker 失败: {e}")
        return
    
    # 发布初始状态
    print("📤 发布初始灯具状态...")
    for light_id in LIGHTS.keys():
        publish_lighting_state(light_id)
        publish_lighting_event(light_id, "INIT", "Lighting simulator initialized")
    
    # 启动房间亮度模拟线程
    brightness_thread = threading.Thread(target=simulate_room_brightness, daemon=True)
    brightness_thread.start()
    print("✓ 房间亮度模拟已启动")
    
    print("="*60)
    print("灯具列表:")
    for light_id, config in LIGHTS.items():
        print(f"  💡 {light_id} - {config['name']}")
    print("="*60)
    print("控制命令主题:")
    for light_id in LIGHTS.keys():
        print(f"  home/lighting/{light_id}/cmd")
        print(f"  home/lighting/{light_id}/auto_adjust")
    print("="*60)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止灯具模拟器...")
        client.loop_stop()
        client.disconnect()
        print("✓ 已停止")


if __name__ == "__main__":
    main()

