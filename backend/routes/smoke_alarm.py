"""
烟雾报警器模块 API 路由
功能：烟雾报警器状态监控、报警记录、测试模式控制
"""

from flask import Blueprint, jsonify, request
from database import (
    upsert_smoke_alarm_state, get_smoke_alarm_state, get_all_smoke_alarms,
    insert_smoke_alarm_event, get_smoke_alarm_events
)

# 创建蓝图
smoke_alarm_bp = Blueprint('smoke_alarm', __name__, url_prefix='/smoke_alarms')


@smoke_alarm_bp.route("", methods=["GET"])
def list_smoke_alarms():
    """获取所有烟雾报警器列表"""
    alarms = get_all_smoke_alarms()
    return jsonify(alarms)


@smoke_alarm_bp.route("/<alarm_id>", methods=["GET"])
def alarm_state(alarm_id):
    """获取烟雾报警器状态"""
    state = get_smoke_alarm_state(alarm_id)
    if state:
        return jsonify(state)
    return jsonify({"error": "烟雾报警器未找到"}), 404


@smoke_alarm_bp.route("/<alarm_id>/test", methods=["POST"])
def test_alarm(alarm_id):
    """启动/停止测试模式"""
    body = request.get_json(force=True) or {}
    test_mode = body.get('test_mode', False)

    # 获取当前状态
    current_state = get_smoke_alarm_state(alarm_id)
    if not current_state:
        return jsonify({"error": "烟雾报警器未找到"}), 404

    # 更新测试模式
    upsert_smoke_alarm_state(
        alarm_id=alarm_id,
        test_mode=test_mode
    )

    # 记录事件
    event_type = 'TEST_STARTED' if test_mode else 'TEST_STOPPED'
    insert_smoke_alarm_event(
        alarm_id=alarm_id,
        event_type=event_type,
        detail=f"Test mode {'activated' if test_mode else 'deactivated'}"
    )

    return jsonify({
        "status": "success",
        "message": f"测试模式已{'启动' if test_mode else '停止'}",
        "alarm_id": alarm_id
    })


@smoke_alarm_bp.route("/<alarm_id>/sensitivity", methods=["POST"])
def update_sensitivity(alarm_id):
    """更新灵敏度设置"""
    body = request.get_json(force=True) or {}
    sensitivity = body.get('sensitivity', 'medium')

    if sensitivity not in ['low', 'medium', 'high']:
        return jsonify({"error": "无效的灵敏度值，必须是 low/medium/high"}), 400

    # 获取当前状态
    current_state = get_smoke_alarm_state(alarm_id)
    if not current_state:
        return jsonify({"error": "烟雾报警器未找到"}), 404

    old_sensitivity = current_state.get('sensitivity')

    # 更新灵敏度
    upsert_smoke_alarm_state(
        alarm_id=alarm_id,
        sensitivity=sensitivity
    )

    # 记录事件
    insert_smoke_alarm_event(
        alarm_id=alarm_id,
        event_type='SENSITIVITY_CHANGED',
        detail=f"Sensitivity changed from {old_sensitivity} to {sensitivity}"
    )

    return jsonify({
        "status": "success",
        "message": f"灵敏度已更新为 {sensitivity}",
        "alarm_id": alarm_id
    })


@smoke_alarm_bp.route("/<alarm_id>/events", methods=["GET"])
def alarm_events(alarm_id):
    """获取烟雾报警器事件历史"""
    limit = request.args.get('limit', 50, type=int)
    events = get_smoke_alarm_events(alarm_id, limit)
    return jsonify(events)


@smoke_alarm_bp.route("/<alarm_id>/acknowledge", methods=["POST"])
def acknowledge_alarm(alarm_id):
    """确认/清除报警"""
    # 获取当前状态
    current_state = get_smoke_alarm_state(alarm_id)
    if not current_state:
        return jsonify({"error": "烟雾报警器未找到"}), 404

    # 清除报警状态
    upsert_smoke_alarm_state(
        alarm_id=alarm_id,
        alarm_active=False
    )

    # 记录事件
    insert_smoke_alarm_event(
        alarm_id=alarm_id,
        event_type='ALARM_ACKNOWLEDGED',
        smoke_level=current_state.get('smoke_level'),
        detail="Alarm acknowledged by user"
    )

    return jsonify({
        "status": "success",
        "message": "报警已确认并清除",
        "alarm_id": alarm_id
    })
