"""
MQTT 客户端模块
订阅温湿度传感器主题，支持多个设备
"""

import paho.mqtt.client as mqtt
import json
from database import insert_sensor_data, upsert_lock_state, insert_lock_event, upsert_lighting_state, insert_lighting_event
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
        # 温湿度
        client.subscribe(MQTT_TOPIC)
        print(f"✓ 已订阅主题: {MQTT_TOPIC}")
        # 门锁状态与事件
        client.subscribe("home/lock/+/state")
        client.subscribe("home/lock/+/event")
        print("✓ 已订阅主题: home/lock/+/state, home/lock/+/event")
        # ------------------------------------------------------------------------------------------------------
        # 灯具状态与事件
        client.subscribe("home/lighting/+/state")
        client.subscribe("home/lighting/+/event")
        print("✓ 已订阅主题: home/lighting/+/state, home/lighting/+/event")
        # ------------------------------------------------------------------------------------------------------
    else:
        print(f"✗ 连接失败，返回码: {rc}")


def on_message(client, userdata, msg):
    """
    消息回调：处理温湿度、门锁与灯具数据
    """
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        
        # 门锁主题处理
        if topic.startswith("home/lock/"):
            parts = topic.split('/')
            lock_id = parts[2] if len(parts) > 2 else 'front_door'
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                data = {}
            if topic.endswith('/state'):
                # 期望: { locked: true/false, method, actor, battery, ts }
                upsert_lock_state(
                    lock_id=lock_id,
                    locked=bool(data.get('locked', False)),  # 默认解锁状态
                    method=data.get('method'),
                    actor=data.get('actor'),
                    battery=data.get('battery'),
                    ts=data.get('ts')
                )
                print(f"📨 [lock:{lock_id}] state locked={data.get('locked')} method={data.get('method')} actor={data.get('actor')}")
            elif topic.endswith('/event'):
                insert_lock_event(
                    lock_id=lock_id,
                    event_type=str(data.get('type', 'event')),
                    method=data.get('method'),
                    actor=data.get('actor'),
                    detail=json.dumps(data.get('detail')) if isinstance(data.get('detail'), (dict, list)) else data.get('detail'),
                    ts=data.get('ts')
                )
                print(f"📨 [lock:{lock_id}] event {data.get('type')} by {data.get('actor')}")
            return
        # ------------------------------------------------------------------------------------------------------    
        # 灯具主题处理
        if topic.startswith("home/lighting/"):
            parts = topic.split('/')
            light_id = parts[2] if len(parts) > 2 else 'light_room1'
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                data = {}
            if topic.endswith('/state'):
                # 期望: { power: true/false, brightness: 0-100, auto_mode: true/false, room_brightness: float, color_temp: int }
                upsert_lighting_state(
                    light_id=light_id,
                    power=data.get('power'),
                    brightness=data.get('brightness'),
                    auto_mode=data.get('auto_mode'),
                    room_brightness=data.get('room_brightness'),
                    color_temp=data.get('color_temp')
                )
                print(f"📨 [light:{light_id}] state power={data.get('power')} brightness={data.get('brightness')}% auto={data.get('auto_mode')}")
            elif topic.endswith('/event'):
                insert_lighting_event(
                    light_id=light_id,
                    event_type=str(data.get('type', 'event')),
                    old_value=data.get('old_value'),
                    new_value=data.get('new_value'),
                    detail=data.get('detail')
                )
                print(f"📨 [light:{light_id}] event {data.get('type')} - {data.get('detail')}")
            return
        # ------------------------------------------------------------------------------------------------------    

        # 温湿度主题处理
        device_id = parse_device_id(topic)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = eval(payload)
        insert_sensor_data(data, device_id)
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


def publish_lock_command(lock_id, action, method, actor=None, pin=None):
    """发布门锁命令到 MQTT。"""
    topic = f"home/lock/{lock_id}/cmd"
    payload = {"action": action, "method": method}
    if actor:
        payload["actor"] = actor
    if pin:
        payload["pin"] = pin
    client.publish(topic, json.dumps(payload))
    print(f"📤 [lock:{lock_id}] cmd -> {payload}")

# ------------------------------------------------------------------------------------------------------
def publish_lighting_command(light_id, power=None, brightness=None, auto_mode=None, color_temp=None):
    """发布灯具控制命令到 MQTT。"""
    topic = f"home/lighting/{light_id}/cmd"
    payload = {}
    if power is not None:
        payload["power"] = power
    if brightness is not None:
        payload["brightness"] = brightness
    if auto_mode is not None:
        payload["auto_mode"] = auto_mode
    if color_temp is not None:
        payload["color_temp"] = color_temp
    
    client.publish(topic, json.dumps(payload))
    print(f"📤 [light:{light_id}] cmd -> {payload}")


def publish_lighting_auto_adjust(light_id, room_brightness):
    """发布灯具智能调节命令到 MQTT。"""
    topic = f"home/lighting/{light_id}/auto_adjust"
    payload = {"room_brightness": room_brightness}
    client.publish(topic, json.dumps(payload))
    print(f"📤 [light:{light_id}] auto_adjust -> {payload}")
# ------------------------------------------------------------------------------------------------------        

  
if __name__ == "__main__":
    print("="*50)
    print("MQTT 客户端运行中...")
    print(f"订阅主题: {MQTT_TOPIC}")
    # ------------------------------------------------------------------------------------------------------
    print("订阅主题: home/lock/+/state, home/lock/+/event")
    print("订阅主题: home/lighting/+/state, home/lighting/+/event")
    # ------------------------------------------------------------------------------------------------------
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
