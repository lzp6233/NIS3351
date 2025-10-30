"""
自动化响应规则 API 路由
功能：管理烟雾报警器的自动化响应规则（跨设备联动）
"""

from flask import Blueprint, jsonify, request
import sys
import os

# 添加当前目录到路径以便导入 database_enhanced
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database_enhanced import (
    get_all_response_rules,
    create_response_rule,
    update_response_rule,
    delete_response_rule
)

# 创建蓝图
automation_bp = Blueprint('automation', __name__, url_prefix='/automation')


@automation_bp.route("/rules", methods=["GET"])
def list_rules():
    """获取所有自动化响应规则"""
    try:
        enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
        rules = get_all_response_rules(enabled_only=enabled_only)
        return jsonify({
            "success": True,
            "count": len(rules),
            "rules": rules
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@automation_bp.route("/rules", methods=["POST"])
def create_rule():
    """创建新的自动化响应规则

    请求体示例:
    {
        "rule_name": "厨房烟雾报警-自动解锁前门",
        "alarm_id": "smoke_kitchen",
        "room_id": "kitchen",
        "trigger_condition": "alarm_triggered",
        "condition_value": 1,
        "action_type": "unlock_door",
        "action_target": "FRONT_DOOR",
        "action_params": {"reason": "emergency_evacuation"},
        "enabled": true,
        "priority": 1
    }
    """
    try:
        data = request.get_json()

        # 验证必填字段
        required = ['rule_name', 'trigger_condition', 'action_type']
        for field in required:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400

        rule_id = create_response_rule(
            rule_name=data['rule_name'],
            alarm_id=data.get('alarm_id'),
            room_id=data.get('room_id'),
            trigger_condition=data['trigger_condition'],
            condition_value=data.get('condition_value'),
            action_type=data['action_type'],
            action_target=data.get('action_target'),
            action_params=data.get('action_params'),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 0)
        )

        return jsonify({
            "success": True,
            "message": "Rule created successfully",
            "rule_id": rule_id
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@automation_bp.route("/rules/<int:rule_id>", methods=["GET"])
def get_rule(rule_id):
    """获取单个规则详情"""
    try:
        rules = get_all_response_rules()
        rule = next((r for r in rules if r['rule_id'] == rule_id), None)

        if not rule:
            return jsonify({
                "success": False,
                "error": "Rule not found"
            }), 404

        return jsonify({
            "success": True,
            "rule": rule
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@automation_bp.route("/rules/<int:rule_id>", methods=["PUT"])
def modify_rule(rule_id):
    """更新自动化规则

    可更新字段: rule_name, alarm_id, room_id, trigger_condition, condition_value,
                action_type, action_target, action_params, enabled, priority
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        success = update_response_rule(rule_id, **data)

        if success:
            return jsonify({
                "success": True,
                "message": "Rule updated successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Rule not found or no changes made"
            }), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@automation_bp.route("/rules/<int:rule_id>", methods=["DELETE"])
def remove_rule(rule_id):
    """删除自动化规则"""
    try:
        success = delete_response_rule(rule_id)

        if success:
            return jsonify({
                "success": True,
                "message": "Rule deleted successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Rule not found"
            }), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@automation_bp.route("/rules/<int:rule_id>/toggle", methods=["POST"])
def toggle_rule(rule_id):
    """快速启用/禁用规则"""
    try:
        data = request.get_json()
        enabled = data.get('enabled')

        if enabled is None:
            return jsonify({
                "success": False,
                "error": "Missing 'enabled' field"
            }), 400

        success = update_response_rule(rule_id, enabled=enabled)

        if success:
            return jsonify({
                "success": True,
                "message": f"Rule {'enabled' if enabled else 'disabled'} successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Rule not found"
            }), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@automation_bp.route("/rules/actions", methods=["GET"])
def list_action_types():
    """获取支持的动作类型列表"""
    action_types = [
        {
            "type": "unlock_door",
            "name": "解锁门锁",
            "description": "紧急情况下自动解锁指定门锁",
            "target_example": "FRONT_DOOR",
            "params_example": {"reason": "emergency_evacuation"}
        },
        {
            "type": "turn_off_ac",
            "name": "关闭空调",
            "description": "防止烟雾通过空调系统扩散",
            "target_example": "ac_kitchen",
            "params_example": {"prevent_smoke_spread": True}
        },
        {
            "type": "turn_on_lights",
            "name": "打开照明",
            "description": "提供紧急照明以便逃生",
            "target_example": "light_living",
            "params_example": {"brightness": 100, "reason": "emergency_lighting"}
        },
        {
            "type": "send_notification",
            "name": "发送通知",
            "description": "向用户发送紧急通知",
            "target_example": "user1",
            "params_example": {"channels": ["email", "sms"], "priority": "high"}
        },
        {
            "type": "trigger_alarm",
            "name": "触发警报",
            "description": "激活其他报警设备",
            "target_example": "siren_main",
            "params_example": {"duration": 60, "volume": "max"}
        }
    ]

    return jsonify({
        "success": True,
        "action_types": action_types
    })


@automation_bp.route("/rules/triggers", methods=["GET"])
def list_trigger_types():
    """获取支持的触发条件类型列表"""
    trigger_types = [
        {
            "type": "alarm_triggered",
            "name": "报警触发",
            "description": "当烟雾报警器触发时",
            "value_type": "boolean",
            "value_example": 1
        },
        {
            "type": "smoke_level_threshold",
            "name": "烟雾浓度阈值",
            "description": "当烟雾浓度超过指定值时",
            "value_type": "float",
            "value_example": 50.0
        },
        {
            "type": "battery_low",
            "name": "电池电量低",
            "description": "当电池电量低于指定值时",
            "value_type": "integer",
            "value_example": 20
        },
        {
            "type": "test_mode_activated",
            "name": "测试模式激活",
            "description": "当设备进入测试模式时",
            "value_type": "boolean",
            "value_example": 1
        }
    ]

    return jsonify({
        "success": True,
        "trigger_types": trigger_types
    })
