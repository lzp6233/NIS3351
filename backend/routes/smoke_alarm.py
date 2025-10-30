"""
烟雾报警器模块 API 路由（增强版）
功能：烟雾报警器状态监控、报警记录、测试模式控制、维护管理、自动化规则、统计分析
"""

import sys
import os
from flask import Blueprint, jsonify, request
from database import (
    upsert_smoke_alarm_state, get_smoke_alarm_state, get_all_smoke_alarms,
    insert_smoke_alarm_event, get_smoke_alarm_events
)

# 添加当前目录到路径以便导入 database_enhanced
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database_enhanced import (
    get_maintenance_records, add_maintenance_record, get_maintenance_due_devices,
    get_all_response_rules, create_response_rule, update_response_rule, delete_response_rule,
    acknowledge_alarm as db_acknowledge_alarm, get_alarm_acknowledgments,
    get_alarm_statistics, update_daily_statistics
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
    """确认/清除报警（增强版）

    请求体示例:
    {
        "acknowledged_by": "张三",
        "event_id": 123,
        "response_time": 45,
        "action_taken": "已确认是厨房做饭产生的烟雾，已开窗通风",
        "resolution": "false_alarm",
        "notes": "建议降低厨房报警器灵敏度"
    }
    """
    try:
        data = request.get_json() or {}

        # 获取当前状态
        current_state = get_smoke_alarm_state(alarm_id)
        if not current_state:
            return jsonify({"error": "烟雾报警器未找到"}), 404

        # 获取参数
        acknowledged_by = data.get('acknowledged_by', 'Unknown User')
        event_id = data.get('event_id')
        response_time = data.get('response_time')
        action_taken = data.get('action_taken')
        resolution = data.get('resolution', 'resolved')
        notes = data.get('notes')

        # 如果没有提供event_id，尝试获取最近的报警事件
        if not event_id:
            recent_events = get_smoke_alarm_events(alarm_id, limit=1)
            if recent_events and recent_events[0].get('event_type') == 'ALARM_TRIGGERED':
                event_id = recent_events[0].get('id')

        # 使用增强的确认函数
        ack_id = db_acknowledge_alarm(
            alarm_id=alarm_id,
            event_id=event_id,
            acknowledged_by=acknowledged_by,
            response_time=response_time,
            action_taken=action_taken,
            resolution=resolution,
            notes=notes
        )

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
            detail=f"Alarm acknowledged by {acknowledged_by}, resolution: {resolution}"
        )

        # 更新统计
        try:
            update_daily_statistics(alarm_id)
        except Exception as e:
            print(f"Warning: Failed to update statistics: {e}")

        return jsonify({
            "status": "success",
            "message": "报警已确认并清除",
            "alarm_id": alarm_id,
            "acknowledgment_id": ack_id,
            "resolution": resolution
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@smoke_alarm_bp.route("/<alarm_id>/acknowledgments", methods=["GET"])
def get_acknowledgments(alarm_id):
    """获取报警确认历史"""
    try:
        limit = request.args.get('limit', 50, type=int)
        acknowledgments = get_alarm_acknowledgments(alarm_id, limit)
        return jsonify({
            "status": "success",
            "alarm_id": alarm_id,
            "count": len(acknowledgments),
            "acknowledgments": acknowledgments
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== 设备维护管理 ====================

@smoke_alarm_bp.route("/<alarm_id>/maintenance", methods=["GET"])
def get_maintenance(alarm_id):
    """获取设备维护记录"""
    try:
        limit = request.args.get('limit', 50, type=int)
        records = get_maintenance_records(alarm_id, limit)
        return jsonify({
            "status": "success",
            "alarm_id": alarm_id,
            "count": len(records),
            "maintenance_records": records
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@smoke_alarm_bp.route("/<alarm_id>/maintenance", methods=["POST"])
def add_maintenance(alarm_id):
    """添加维护记录

    请求体示例:
    {
        "maintenance_type": "battery_replacement",
        "performed_by": "技术人员-李四",
        "maintenance_date": "2025-10-30T10:00:00",
        "next_maintenance_date": "2026-10-30T10:00:00",
        "notes": "更换9V电池",
        "cost": 15.00
    }
    """
    try:
        data = request.get_json()

        # 验证必填字段
        required = ['maintenance_type', 'performed_by']
        for field in required:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "error": f"Missing required field: {field}"
                }), 400

        # 验证维护类型
        valid_types = ['battery_replacement', 'cleaning', 'test', 'inspection', 'repair']
        if data['maintenance_type'] not in valid_types:
            return jsonify({
                "status": "error",
                "error": f"Invalid maintenance_type. Must be one of: {', '.join(valid_types)}"
            }), 400

        record_id = add_maintenance_record(
            alarm_id=alarm_id,
            maintenance_type=data['maintenance_type'],
            performed_by=data['performed_by'],
            maintenance_date=data.get('maintenance_date'),
            next_maintenance_date=data.get('next_maintenance_date'),
            notes=data.get('notes'),
            cost=data.get('cost')
        )

        # 记录事件
        insert_smoke_alarm_event(
            alarm_id=alarm_id,
            event_type='MAINTENANCE_PERFORMED',
            detail=f"{data['maintenance_type']} performed by {data['performed_by']}"
        )

        return jsonify({
            "status": "success",
            "message": "维护记录已添加",
            "record_id": record_id
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@smoke_alarm_bp.route("/maintenance/due", methods=["GET"])
def get_maintenance_due():
    """获取需要维护的设备列表"""
    try:
        days_ahead = request.args.get('days_ahead', 30, type=int)
        devices = get_maintenance_due_devices(days_ahead)
        return jsonify({
            "status": "success",
            "count": len(devices),
            "devices": devices
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== 统计分析 ====================

@smoke_alarm_bp.route("/<alarm_id>/statistics", methods=["GET"])
def get_statistics(alarm_id):
    """获取单个报警器的统计数据"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        stats = get_alarm_statistics(
            alarm_id=alarm_id,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify({
            "status": "success",
            "alarm_id": alarm_id,
            "count": len(stats),
            "statistics": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@smoke_alarm_bp.route("/statistics", methods=["GET"])
def get_all_statistics():
    """获取所有报警器的统计数据"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        stats = get_alarm_statistics(
            start_date=start_date,
            end_date=end_date
        )

        # 按报警器分组
        grouped = {}
        for stat in stats:
            alarm_id = stat['alarm_id']
            if alarm_id not in grouped:
                grouped[alarm_id] = []
            grouped[alarm_id].append(stat)

        # 计算汇总数据
        summary = {
            "total_alarms": sum(s['total_alarms'] for s in stats),
            "false_alarms": sum(s['false_alarms'] for s in stats),
            "real_alarms": sum(s['real_alarms'] for s in stats),
            "devices_count": len(grouped)
        }

        if stats:
            summary["false_alarm_rate"] = round(
                (summary["false_alarms"] / summary["total_alarms"] * 100) if summary["total_alarms"] > 0 else 0,
                2
            )

        return jsonify({
            "status": "success",
            "summary": summary,
            "by_device": grouped,
            "all_stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
