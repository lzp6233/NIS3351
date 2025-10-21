"""
智慧门锁模拟器（单把：FRONT_DOOR）
订阅命令：home/lock/FRONT_DOOR/cmd
上报状态：home/lock/FRONT_DOOR/state
上报事件：home/lock/FRONT_DOOR/event
"""

import time
import json
import random
from datetime import datetime
import paho.mqtt.client as mqtt

# 简化配置：使用与 sensor_sim 相同的 broker 配置
from config import MQTT_BROKER, MQTT_PORT

LOCK_ID = 'FRONT_DOOR'


class LockState:
    def __init__(self):
        self.locked = True
        self.battery = 100
        self.last_method = None
        self.last_actor = None

    def drain_battery(self, amount=1):
        self.battery = max(0, self.battery - amount)


state = LockState()


def now_iso():
    return datetime.utcnow().isoformat()


def publish_state(client):
    payload = {
        "locked": state.locked,
        "method": state.last_method,
        "actor": state.last_actor,
        "battery": state.battery,
        "ts": now_iso(),
    }
    client.publish(f"home/lock/{LOCK_ID}/state", json.dumps(payload))
    print(f"📤 [lock:{LOCK_ID}] state -> {payload}")


def publish_event(client, type_, detail=None):
    payload = {
        "type": type_,
        "method": state.last_method,
        "actor": state.last_actor,
        "detail": detail,
        "ts": now_iso(),
    }
    client.publish(f"home/lock/{LOCK_ID}/event", json.dumps(payload))
    print(f"📤 [lock:{LOCK_ID}] event -> {payload}")


EXPECTED_PIN = "1234"  # 演示用，真实应在后端校验


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✓ 锁模拟器已连接 MQTT: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(f"home/lock/{LOCK_ID}/cmd")
        print(f"✓ 订阅: home/lock/{LOCK_ID}/cmd")
        # 上线时上报一次状态
        publish_state(client)
    else:
        print(f"✗ 连接失败: {rc}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        data = {}

    action = data.get("action")
    method = data.get("method")  # PINCODE/FINGERPRINT/APP/REMOTE/KEY
    actor = data.get("actor") or "unknown"
    pin = data.get("pin")

    state.last_method = method
    state.last_actor = actor

    # 简单电量模型：每次操作消耗 1-2 点
    state.drain_battery(random.randint(1, 2))

    if action == "unlock":
        if method == "PINCODE":
            if pin == EXPECTED_PIN:
                state.locked = False
                publish_state(client)
                publish_event(client, "unlock_success")
            else:
                publish_event(client, "unlock_fail", detail="invalid_pin")
        else:
            # 其他方式直接成功
            state.locked = False
            publish_state(client)
            publish_event(client, "unlock_success")
    elif action == "lock":
        state.locked = True
        publish_state(client)
        publish_event(client, "lock")
    else:
        publish_event(client, "unknown_cmd", detail=data)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    print("✓ 锁模拟器已启动")
    try:
        while True:
            # 周期性健康上报（例如每 30 秒）
            time.sleep(30)
            publish_state(client)
    except KeyboardInterrupt:
        print("\n停止锁模拟器...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()


