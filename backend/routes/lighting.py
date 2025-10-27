"""
灯具控制模块 API 路由
负责人：lzx
功能：全屋灯具控制、智能调节模式、亮度控制
"""

from flask import Blueprint, jsonify, request
from database import (
    upsert_lighting_state, get_lighting_state, get_all_lights,
    insert_lighting_event, get_lighting_events
)

# 创建蓝图
lighting_bp = Blueprint('lighting', __name__)


@lighting_bp.route("/lighting", methods=["GET"])
def list_lights():
    """获取所有灯具列表"""
    lights = get_all_lights()
    return jsonify(lights)


@lighting_bp.route("/lighting/<light_id>", methods=["GET"])
def lighting_state(light_id):
    """获取灯具状态"""
    state = get_lighting_state(light_id)
    if state:
        return jsonify(state)
    return jsonify({"error": "灯具未找到"}), 404


@lighting_bp.route("/lighting/<light_id>/control", methods=["POST"])
def control_lighting(light_id):
    """控制灯具（开关、亮度、智能模式等）"""
    body = request.get_json(force=True) or {}
    
    # 获取当前状态
    current_state = get_lighting_state(light_id)
    
    # 提取控制参数
    power = body.get('power')  # True/False
    brightness = body.get('brightness')  # 0-100
    auto_mode = body.get('auto_mode')  # True/False
    color_temp = body.get('color_temp')  # 色温
    device_id = body.get('device_id', 'room1')
    
    # 记录旧值（用于事件日志）
    old_power = current_state.get('power') if current_state else False
    old_brightness = current_state.get('brightness') if current_state else None
    old_auto_mode = current_state.get('auto_mode') if current_state else None
    old_color_temp = current_state.get('color_temp') if current_state else None
    
    # 新的控制逻辑：
    # 1. 开灯状态下：与房间亮度无关，只受到用户手动调节
    # 2. 关灯条件下：用户选择是否开启"智能控制"，然后根据用户的选择实现
    
    # 如果关闭智能模式，确保灯具关闭
    if auto_mode is False:
        power = False
    
    # 如果开启智能模式，但当前是关灯状态，保持关灯（等待自动调节）
    if auto_mode is True and power is None and old_power is False:
        power = False
    
    # 更新灯具状态
    upsert_lighting_state(
        light_id=light_id,
        device_id=device_id,
        power=power,
        brightness=brightness,
        auto_mode=auto_mode,
        color_temp=color_temp
    )
    
    # 记录事件
    if power is not None and power != old_power:
        event_type = 'power_on' if power else 'power_off'
        insert_lighting_event(
            light_id=light_id,
            event_type=event_type,
            old_value=str(old_power),
            new_value=str(power),
            detail=f"Manual control: Light {'turned on' if power else 'turned off'}"
        )
    
    if brightness is not None and brightness != old_brightness:
        insert_lighting_event(
            light_id=light_id,
            event_type='brightness_change',
            old_value=str(old_brightness) if old_brightness else None,
            new_value=str(brightness),
            detail=f"Manual control: Brightness set to {brightness}%"
        )
    
    if auto_mode is not None and auto_mode != old_auto_mode:
        insert_lighting_event(
            light_id=light_id,
            event_type='auto_mode_change',
            old_value=str(old_auto_mode),
            new_value=str(auto_mode),
            detail=f"Manual control: Auto mode {'enabled' if auto_mode else 'disabled'}"
        )
    
    if color_temp is not None and color_temp != old_color_temp:
        insert_lighting_event(
            light_id=light_id,
            event_type='color_temp_change',
            old_value=str(old_color_temp) if old_color_temp else None,
            new_value=str(color_temp),
            detail=f"Manual control: Color temperature set to {color_temp}K"
        )
    
    return jsonify({
        "status": "success",
        "message": "灯具控制成功",
        "light_id": light_id,
        "power": power,
        "brightness": brightness,
        "auto_mode": auto_mode
    })


@lighting_bp.route("/lighting/<light_id>/events", methods=["GET"])
def lighting_events(light_id):
    """获取灯具事件历史"""
    limit = request.args.get('limit', 50, type=int)
    events = get_lighting_events(light_id, limit)
    return jsonify(events)


@lighting_bp.route("/lighting/<light_id>/auto-adjust", methods=["POST"])
def auto_adjust_lighting(light_id):
    """智能调节灯具亮度（根据房间亮度）"""
    body = request.get_json(force=True) or {}
    room_brightness = body.get('room_brightness', 0)  # 房间亮度传感器读数
    
    # 获取当前状态
    current_state = get_lighting_state(light_id)
    if not current_state:
        return jsonify({"error": "灯具未找到"}), 404
    
    # 如果智能模式未开启，不进行自动调节
    if not current_state.get('auto_mode', False):
        return jsonify({
            "status": "info",
            "message": "智能调节模式未开启",
            "light_id": light_id
        })
    
    # 新的智能控制逻辑：
    # 1. 未开启"智能控制"时，保持关灯状态
    # 2. 开启"智能控制"时，当房间亮度低于某个值时，自动开灯
    
    # 设置房间亮度阈值（低于此值自动开灯）
    brightness_threshold = 30  # lux
    
    old_power = current_state.get('power', False)
    old_brightness = current_state.get('brightness', 50)
    
    # 智能控制逻辑
    if room_brightness < brightness_threshold:
        # 房间太暗，自动开灯
        if not old_power:
            upsert_lighting_state(
                light_id=light_id,
                power=True,
                brightness=70,  # 默认亮度70%
                room_brightness=room_brightness
            )
            
            # 记录事件
            insert_lighting_event(
                light_id=light_id,
                event_type='auto_power_on',
                old_value=str(old_power),
                new_value='True',
                detail=f"Auto turned on due to low room brightness ({room_brightness} lux < {brightness_threshold} lux)"
            )
            
            return jsonify({
                "status": "success",
                "message": f"房间亮度过低({room_brightness} lux)，已自动开灯",
                "light_id": light_id,
                "room_brightness": room_brightness,
                "action": "turned_on",
                "brightness": 70
            })
        else:
            # 灯已开启，保持当前状态
            return jsonify({
                "status": "info",
                "message": f"灯已开启，房间亮度: {room_brightness} lux",
                "light_id": light_id,
                "room_brightness": room_brightness,
                "action": "maintained"
            })
    else:
        # 房间亮度足够，自动关灯
        if old_power:
            upsert_lighting_state(
                light_id=light_id,
                power=False,
                room_brightness=room_brightness
            )
            
            # 记录事件
            insert_lighting_event(
                light_id=light_id,
                event_type='auto_power_off',
                old_value=str(old_power),
                new_value='False',
                detail=f"Auto turned off due to sufficient room brightness ({room_brightness} lux >= {brightness_threshold} lux)"
            )
            
            return jsonify({
                "status": "success",
                "message": f"房间亮度充足({room_brightness} lux)，已自动关灯",
                "light_id": light_id,
                "room_brightness": room_brightness,
                "action": "turned_off"
            })
        else:
            # 灯已关闭，保持当前状态
            return jsonify({
                "status": "info",
                "message": f"灯已关闭，房间亮度: {room_brightness} lux",
                "light_id": light_id,
                "room_brightness": room_brightness,
                "action": "maintained"
            })


@lighting_bp.route("/lighting/batch-control", methods=["POST"])
def batch_control_lighting():
    """批量控制多个灯具"""
    body = request.get_json(force=True) or {}
    lights = body.get('lights', [])  # [{"light_id": "light_room1", "power": true, "brightness": 80}, ...]
    
    results = []
    for light_config in lights:
        light_id = light_config.get('light_id')
        if not light_id:
            continue
            
        # 获取当前状态
        current_state = get_lighting_state(light_id)
        
        # 提取控制参数
        power = light_config.get('power')
        brightness = light_config.get('brightness')
        auto_mode = light_config.get('auto_mode')
        color_temp = light_config.get('color_temp')
        
        # 更新灯具状态
        upsert_lighting_state(
            light_id=light_id,
            power=power,
            brightness=brightness,
            auto_mode=auto_mode,
            color_temp=color_temp
        )
        
        results.append({
            "light_id": light_id,
            "status": "success"
        })
    
    return jsonify({
        "status": "success",
        "message": f"批量控制完成，共处理 {len(results)} 个灯具",
        "results": results
    })







