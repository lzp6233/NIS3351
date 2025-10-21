"""
空调模块 API 路由
负责人：lzp
功能：空调控制、温湿度监控、历史数据查询
"""

from flask import Blueprint, jsonify, request
from database import (
    get_recent_data, get_devices, get_latest_data,
    upsert_ac_state, get_ac_state, get_all_acs, 
    insert_ac_event, get_ac_events
)

# 创建蓝图
air_conditioner_bp = Blueprint('air_conditioner', __name__)


@air_conditioner_bp.route("/devices", methods=["GET"])
def devices():
    """获取所有设备列表"""
    print(f"收到设备列表请求 - Method: {request.method}, Origin: {request.headers.get('Origin')}")
    data = get_devices()
    return jsonify(data)


@air_conditioner_bp.route("/history")
def history():
    """获取所有设备的历史数据"""
    limit = request.args.get('limit', 100, type=int)
    data = get_recent_data(limit=limit)
    return jsonify(data)


@air_conditioner_bp.route("/history/<device_id>")
def history_by_device(device_id):
    """获取指定设备的历史数据"""
    limit = request.args.get('limit', 100, type=int)
    data = get_recent_data(device_id=device_id, limit=limit)
    return jsonify(data)


@air_conditioner_bp.route("/latest/<device_id>")
def latest(device_id):
    """获取指定设备的最新数据"""
    data = get_latest_data(device_id)
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "设备未找到"}), 404


# ==================== 空调控制 API ====================

@air_conditioner_bp.route("/ac", methods=["GET"])
def list_acs():
    """获取所有空调列表"""
    acs = get_all_acs()
    return jsonify(acs)


@air_conditioner_bp.route("/ac/<ac_id>", methods=["GET"])
def ac_state(ac_id):
    """获取空调状态"""
    state = get_ac_state(ac_id)
    if state:
        # 获取最新的温湿度数据
        device_id = state.get('device_id', 'room1')
        latest_data = get_latest_data(device_id)
        if latest_data:
            state['current_temp'] = latest_data['temperature']
            state['current_humidity'] = latest_data['humidity']
            # 更新数据库中的当前温湿度
            upsert_ac_state(
                ac_id, 
                current_temp=latest_data['temperature'],
                current_humidity=latest_data['humidity']
            )
        return jsonify(state)
    return jsonify({"error": "空调未找到"}), 404


@air_conditioner_bp.route("/ac/<ac_id>/control", methods=["POST"])
def control_ac(ac_id):
    """控制空调（开关、温度设置等）"""
    body = request.get_json(force=True) or {}
    
    # 获取当前状态
    current_state = get_ac_state(ac_id)
    
    # 提取控制参数
    power = body.get('power')  # True/False
    target_temp = body.get('target_temp')  # 目标温度
    mode = body.get('mode')  # cool/heat/fan
    fan_speed = body.get('fan_speed')  # low/medium/high/auto
    device_id = body.get('device_id', 'room1')
    
    # 记录旧值（用于事件日志）
    old_power = current_state['power'] if current_state else False
    old_temp = current_state['target_temp'] if current_state else None
    
    # 更新空调状态
    upsert_ac_state(
        ac_id=ac_id,
        device_id=device_id,
        power=power,
        mode=mode,
        target_temp=target_temp,
        fan_speed=fan_speed
    )
    
    # 记录事件
    if power is not None and power != old_power:
        event_type = 'power_on' if power else 'power_off'
        insert_ac_event(
            ac_id=ac_id,
            event_type=event_type,
            old_value=str(old_power),
            new_value=str(power),
            detail=f"空调{'开启' if power else '关闭'}"
        )
    
    if target_temp is not None and target_temp != old_temp:
        insert_ac_event(
            ac_id=ac_id,
            event_type='temp_change',
            old_value=str(old_temp) if old_temp else None,
            new_value=str(target_temp),
            detail=f"目标温度设置为 {target_temp}°C"
        )
    
    return jsonify({
        "status": "success",
        "message": "空调控制成功",
        "ac_id": ac_id
    })


@air_conditioner_bp.route("/ac/<ac_id>/events", methods=["GET"])
def ac_events(ac_id):
    """获取空调事件历史"""
    limit = request.args.get('limit', 50, type=int)
    events = get_ac_events(ac_id, limit)
    return jsonify(events)

