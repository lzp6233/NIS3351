"""
智慧门锁模拟器（单把：FRONT_DOOR）
订阅命令：home/lock/FRONT_DOOR/cmd
上报状态：home/lock/FRONT_DOOR/state
上报事件：home/lock/FRONT_DOOR/event
"""

import time
import json
import random
import sys
import os
import threading
from datetime import datetime
import paho.mqtt.client as mqtt

# 添加 backend 路径以导入配置
current_dir = os.path.dirname(__file__)
backend_dir = os.path.join(current_dir, '..', 'backend')
sys.path.insert(0, backend_dir)

# 从统一的配置文件导入
from config import MQTT_BROKER, MQTT_PORT, GLOBAL_PINCODE
from database import get_auto_lock_config

LOCK_ID = 'FRONT_DOOR'


class LockState:
    def __init__(self):
        self.locked = True
        self.battery = 100
        self.last_method = None
        self.last_actor = None
        self.auto_lock_timer = None
        self.auto_lock_delay = 5  # 默认5秒自动锁定

    def drain_battery(self, amount=1):
        self.battery = max(0, self.battery - amount)
    
    def start_auto_lock_timer(self, client, delay=None):
        """启动自动锁定定时器"""
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
        
        # 从数据库获取自动锁定配置
        try:
            config = get_auto_lock_config(LOCK_ID)
            if not config['auto_lock_enabled']:
                print("⏰ 自动锁定已禁用")
                return
            
            delay = delay or config['auto_lock_delay']
            self.auto_lock_delay = delay  # 更新延迟时间
        except Exception as e:
            print(f"⚠ 获取自动锁定配置失败，使用默认值: {e}")
            delay = delay or self.auto_lock_delay
        
        self.auto_lock_timer = threading.Timer(delay, self._auto_lock, args=[client])
        self.auto_lock_timer.start()
        print(f"⏰ 自动锁定定时器已启动，{delay}秒后自动上锁")
    
    def _auto_lock(self, client):
        """自动锁定执行函数"""
        if not self.locked:  # 只有在解锁状态下才执行自动锁定
            self.locked = True
            self.last_method = "AUTO"
            self.last_actor = "System"
            publish_state(client)
            publish_event(client, "auto_lock", detail=f"自动锁定（{self.auto_lock_delay}秒后）")
            print(f"🔒 自动锁定已执行")
    
    def cancel_auto_lock_timer(self):
        """取消自动锁定定时器"""
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
            self.auto_lock_timer = None
            print("❌ 自动锁定定时器已取消")


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


def get_current_pincode():
    """动态获取当前全局PINCODE"""
    try:
        # 使用新的PINCODE配置系统
        from pincode_config import get_pincode
        return get_pincode()
    except:
        return GLOBAL_PINCODE  # 回退到初始值


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
            current_pin = get_current_pincode()
            if pin == current_pin:
                state.locked = False
                publish_state(client)
                publish_event(client, "unlock_success")
                # 启动自动锁定定时器
                state.start_auto_lock_timer(client)
            else:
                publish_event(client, "unlock_fail", detail="invalid_pin")
        else:
            # 其他方式直接成功
            state.locked = False
            publish_state(client)
            publish_event(client, "unlock_success")
            # 启动自动锁定定时器
            state.start_auto_lock_timer(client)
    elif action == "lock":
        state.locked = True
        # 取消自动锁定定时器（如果存在）
        state.cancel_auto_lock_timer()
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
            # 周期性健康上报（每 1 秒）
            time.sleep(1)
            publish_state(client)
    except KeyboardInterrupt:
        print("\n停止锁模拟器...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()


