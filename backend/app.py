"""
Flask Web 服务器
提供 API 接口和 WebSocket 实时推送
"""

from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS
from database import (
    get_recent_data, get_devices, get_latest_data,
    get_all_locks, get_lock_state, get_lock_events, upsert_lock_state, insert_lock_event
)
from config import FLASK_HOST, FLASK_PORT
from mqtt_client import publish_lock_command

app = Flask(__name__)
CORS(app)  # 允许跨域请求
socketio = SocketIO(app, cors_allowed_origins="*")


@app.route("/")
def index():
    """首页"""
    return jsonify({
        "message": "NIS3351 智能家居监控系统 API",
        "endpoints": {
            "/devices": "获取所有设备列表",
            "/history": "获取历史数据",
            "/history/<device_id>": "获取指定设备的历史数据",
            "/latest/<device_id>": "获取指定设备的最新数据"
        }
    })


@app.route("/devices")
def devices():
    """获取所有设备列表"""
    data = get_devices()
    return jsonify(data)


@app.route("/history")
def history():
    """获取所有设备的历史数据"""
    limit = request.args.get('limit', 100, type=int)
    data = get_recent_data(limit=limit)
    return jsonify(data)


@app.route("/history/<device_id>")
def history_by_device(device_id):
    """获取指定设备的历史数据"""
    limit = request.args.get('limit', 100, type=int)
    data = get_recent_data(device_id=device_id, limit=limit)
    return jsonify(data)


@app.route("/latest/<device_id>")
def latest(device_id):
    """获取指定设备的最新数据"""
    data = get_latest_data(device_id)
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "设备未找到"}), 404


# ==================== 智慧门锁 API ====================
@app.route("/locks", methods=["GET"])
def list_locks():
    """列出所有门锁（本项目单把：front_door）"""
    return jsonify(get_all_locks())


@app.route("/locks/<lock_id>/state", methods=["GET"])
def lock_state(lock_id):
    state = get_lock_state(lock_id)
    if state:
        return jsonify(state)
    return jsonify({"error": "not found"}), 404


@app.route("/locks/<lock_id>/events", methods=["GET"])
def lock_events(lock_id):
    limit = request.args.get('limit', 50, type=int)
    return jsonify(get_lock_events(lock_id, limit))


@app.route("/locks/<lock_id>/command", methods=["POST"])
def lock_command(lock_id):
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


if __name__ == "__main__":
    print("="*60)
    print("Flask Web 服务器启动")
    print("="*60)
    print("API 端点:")
    print("  GET  /devices              - 获取设备列表")
    print("  GET  /history              - 获取所有历史数据")
    print("  GET  /history/<device_id>  - 获取指定设备历史数据")
    print("  GET  /latest/<device_id>   - 获取指定设备最新数据")
    print("="*60)
    socketio.run(app, host=FLASK_HOST, port=FLASK_PORT, debug=False, allow_unsafe_werkzeug=True)
