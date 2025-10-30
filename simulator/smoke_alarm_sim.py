"""
烟雾报警器模拟器
模拟多个烟雾报警器设备，生成烟雾浓度数据并触发报警
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
from config import MQTT_BROKER, MQTT_PORT, SMOKE_ALARM_INTERVAL

# 烟雾报警器配置（5个房间）
SMOKE_ALARMS = [
    {
        "alarm_id": "smoke_living_room",
        "location": "living_room",
        "name": "客厅",
        "sensitivity": "medium",  # 灵敏度：low/medium/high
        "alarm_threshold": 30.0   # 报警阈值（烟雾浓度）
    },
    {
        "alarm_id": "smoke_bedroom1",
        "location": "bedroom1",
        "name": "主卧",
        "sensitivity": "medium",
        "alarm_threshold": 30.0
    },
    {
        "alarm_id": "smoke_bedroom2",
        "location": "bedroom2",
        "name": "次卧",
        "sensitivity": "medium",
        "alarm_threshold": 30.0
    },
    {
        "alarm_id": "smoke_kitchen",
        "location": "kitchen",
        "name": "厨房",
        "sensitivity": "high",    # 厨房使用高灵敏度
        "alarm_threshold": 25.0   # 厨房阈值较低
    },
    {
        "alarm_id": "smoke_study",
        "location": "study",
        "name": "书房",
        "sensitivity": "medium",
        "alarm_threshold": 30.0
    }
]

# 每个设备的当前状态
device_states = {}


def generate_smoke_level(alarm_id, location):
    """
    生成烟雾浓度数据（0-100）
    大多数时候保持低浓度，偶尔模拟烟雾事件
    """
    if alarm_id not in device_states:
        device_states[alarm_id] = {
            'smoke_level': 0.0,
            'alarm_active': False,
            'battery': 100,
            'test_mode': False,
            'last_alarm_time': 0
        }

    state = device_states[alarm_id]

    # 如果在测试模式，生成固定的烟雾值
    if state['test_mode']:
        return 50.0

    # 90% 的时间烟雾浓度很低（0-5）
    # 5% 的时间烟雾浓度中等（5-20）
    # 5% 的时间烟雾浓度高（20-80）模拟真实烟雾

    rand = random.random()

    if rand < 0.90:
        # 正常情况：低烟雾浓度
        smoke_level = round(random.uniform(0, 5), 1)
    elif rand < 0.95:
        # 中等烟雾（可能是炒菜、蒸汽等）
        smoke_level = round(random.uniform(5, 20), 1)
    else:
        # 高烟雾浓度（模拟真实火灾/烟雾事件）
        smoke_level = round(random.uniform(20, 80), 1)
        print(f"🔥 [{alarm_id}] 检测到高浓度烟雾: {smoke_level}!")

    return smoke_level


def publish_state(client, alarm_config):
    """发布烟雾报警器状态到 MQTT"""
    alarm_id = alarm_config['alarm_id']
    location = alarm_config['location']
    sensitivity = alarm_config['sensitivity']
    alarm_threshold = alarm_config['alarm_threshold']

    # 生成烟雾浓度
    smoke_level = generate_smoke_level(alarm_id, location)

    state = device_states[alarm_id]
    state['smoke_level'] = smoke_level

    # 根据灵敏度调整阈值
    if sensitivity == 'high':
        threshold = alarm_threshold * 0.8
    elif sensitivity == 'low':
        threshold = alarm_threshold * 1.2
    else:  # medium
        threshold = alarm_threshold

    # 判断是否触发报警
    current_time = time.time()
    if smoke_level >= threshold:
        if not state['alarm_active']:
            # 触发报警
            state['alarm_active'] = True
            state['last_alarm_time'] = current_time

            # 发布报警事件
            event_data = {
                "type": "ALARM_TRIGGERED",
                "smoke_level": smoke_level,
                "detail": f"Smoke level {smoke_level} exceeded threshold {threshold}"
            }
            client.publish(
                f"home/smoke_alarm/{alarm_id}/event",
                json.dumps(event_data)
            )
            print(f"🚨 [{alarm_id}] 报警触发! 烟雾浓度: {smoke_level}")
    else:
        if state['alarm_active']:
            # 解除报警
            state['alarm_active'] = False

            # 发布解除事件
            event_data = {
                "type": "ALARM_CLEARED",
                "smoke_level": smoke_level,
                "detail": f"Smoke level {smoke_level} below threshold {threshold}"
            }
            client.publish(
                f"home/smoke_alarm/{alarm_id}/event",
                json.dumps(event_data)
            )
            print(f"✅ [{alarm_id}] 报警解除. 烟雾浓度: {smoke_level}")

    # 模拟电池消耗（每次降低 0.01%）
    state['battery'] = max(0, state['battery'] - 0.01)

    # 如果电池低于 20%，发送低电量事件（每小时最多一次）
    if state['battery'] < 20 and state['battery'] > 0:
        if not hasattr(state, 'last_low_battery_warning') or \
           (current_time - state.get('last_low_battery_warning', 0)) > 3600:
            event_data = {
                "type": "LOW_BATTERY",
                "smoke_level": smoke_level,
                "detail": f"Battery level: {int(state['battery'])}%"
            }
            client.publish(
                f"home/smoke_alarm/{alarm_id}/event",
                json.dumps(event_data)
            )
            state['last_low_battery_warning'] = current_time
            print(f"🔋 [{alarm_id}] 低电量警告: {int(state['battery'])}%")

    # 发布状态
    state_data = {
        "location": location,
        "smoke_level": smoke_level,
        "alarm_active": state['alarm_active'],
        "battery": int(state['battery']),
        "test_mode": state['test_mode'],
        "sensitivity": sensitivity
    }

    topic = f"home/smoke_alarm/{alarm_id}/state"
    client.publish(topic, json.dumps(state_data))

    # 打印状态信息
    alarm_status = "🚨 报警" if state['alarm_active'] else "✓ 正常"
    print(f"📡 [{alarm_id}] {alarm_status} | 烟雾: {smoke_level}% | 电池: {int(state['battery'])}%")


def on_connect(client, userdata, flags, rc):
    """MQTT 连接回调"""
    if rc == 0:
        print(f"✓ 已连接到 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"✓ 模拟 {len(SMOKE_ALARMS)} 个烟雾报警器")

        # 订阅命令主题（用于测试模式等）
        for alarm in SMOKE_ALARMS:
            alarm_id = alarm['alarm_id']
            client.subscribe(f"home/smoke_alarm/{alarm_id}/cmd")

            # 发送初始化事件
            event_data = {
                "type": "INIT",
                "smoke_level": 0.0,
                "detail": "Smoke alarm simulator started"
            }
            client.publish(
                f"home/smoke_alarm/{alarm_id}/event",
                json.dumps(event_data)
            )

        print("✓ 已订阅命令主题")
    else:
        print(f"✗ 连接失败，返回码: {rc}")


def on_message(client, userdata, msg):
    """处理命令消息（如测试模式切换）"""
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())

        # 提取 alarm_id
        parts = topic.split('/')
        if len(parts) >= 3:
            alarm_id = parts[2]

            if alarm_id in device_states:
                # 处理测试模式命令
                if 'test_mode' in payload:
                    device_states[alarm_id]['test_mode'] = payload['test_mode']
                    print(f"🔧 [{alarm_id}] 测试模式: {payload['test_mode']}")

                # 处理灵敏度变更
                if 'sensitivity' in payload:
                    print(f"🔧 [{alarm_id}] 灵敏度变更: {payload['sensitivity']}")

    except Exception as e:
        print(f"✗ 处理命令时出错: {e}")


def main():
    """主函数"""
    print("="*60)
    print("烟雾报警器模拟器启动")
    print("="*60)

    # 创建 MQTT 客户端
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message

    # 连接到 MQTT Broker
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"✗ 连接 MQTT Broker 失败: {e}")
        print("  请确保 MQTT Broker 正在运行")
        return

    # 主循环：定期发布数据
    try:
        while True:
            for alarm_config in SMOKE_ALARMS:
                publish_state(client, alarm_config)

            time.sleep(SMOKE_ALARM_INTERVAL)

    except KeyboardInterrupt:
        print("\n正在停止烟雾报警器模拟器...")
        client.loop_stop()
        client.disconnect()
        print("✓ 已停止")


if __name__ == "__main__":
    main()
