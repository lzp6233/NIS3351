"""
智能门锁模块 API 路由
负责人：[门锁模块负责人]
功能：门锁状态管理、开锁/上锁控制、事件记录
"""

from flask import Blueprint, jsonify, request
from database import (
    get_all_locks, get_lock_state, get_lock_events, 
    insert_lock_event
)
from mqtt_client import publish_lock_command

# 创建蓝图
lock_bp = Blueprint('lock', __name__, url_prefix='/locks')


@lock_bp.route("", methods=["GET"])
def list_locks():
    """列出所有门锁（本项目单把：FRONT_DOOR）"""
    return jsonify(get_all_locks())


@lock_bp.route("/<lock_id>/state", methods=["GET"])
def lock_state(lock_id):
    """获取指定门锁的状态"""
    state = get_lock_state(lock_id)
    if state:
        return jsonify(state)
    return jsonify({"error": "not found"}), 404


@lock_bp.route("/<lock_id>/events", methods=["GET"])
def lock_events(lock_id):
    """获取指定门锁的事件历史"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify(get_lock_events(lock_id, limit))


@lock_bp.route("/<lock_id>/command", methods=["POST"])
def lock_command(lock_id):
    """发送门锁控制命令（上锁/解锁）"""
    body = request.get_json(force=True) or {}
    action = body.get('action')  # lock / unlock
    method = body.get('method')  # PINCODE/FINGERPRINT/APP/REMOTE/KEY
    actor = body.get('actor')
    pin = body.get('pin')  # 仅当 method=PINCODE 时使用

    if action not in ("lock", "unlock"):
        return jsonify({"error": "invalid action"}), 400
    if method not in ("PINCODE", "FINGERPRINT", "APP", "REMOTE", "KEY"):
        return jsonify({"error": "invalid method"}), 400

    # 发布到 MQTT，由模拟器/真实设备执行，然后设备会回传 state/event
    publish_lock_command(lock_id, action, method=method, actor=actor, pin=pin)

    # 记录命令事件（可选立即记一条）
    insert_lock_event(lock_id, event_type=f"cmd_{action}", method=method, actor=actor, detail="command_sent")
    return jsonify({"status": "sent"})

