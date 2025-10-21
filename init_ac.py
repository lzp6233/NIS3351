#!/usr/bin/env python3
"""
初始化空调状态
为每个房间创建一个空调
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import upsert_ac_state

# 初始化空调
acs = [
    {'ac_id': 'ac_room1', 'device_id': 'room1', 'power': False, 'target_temp': 26.0},
    {'ac_id': 'ac_room2', 'device_id': 'room2', 'power': False, 'target_temp': 26.0},
]

print("="*60)
print("初始化空调状态")
print("="*60)

for ac in acs:
    upsert_ac_state(
        ac_id=ac['ac_id'],
        device_id=ac['device_id'],
        power=ac['power'],
        mode='cool',
        target_temp=ac['target_temp'],
        fan_speed='auto'
    )
    print(f"✓ 已初始化: {ac['ac_id']} ({ac['device_id']}) - 目标温度: {ac['target_temp']}°C")

print("="*60)
print("初始化完成！")
print("\n你现在可以:")
print("1. 启动系统: sh run.sh")
print("2. 访问前端: http://localhost:8000/air-conditioner.html")
print("3. 控制空调，观察温度变化")
print("="*60)

