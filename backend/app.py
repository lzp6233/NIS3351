"""
Flask Web 服务器
提供 API 接口和 WebSocket 实时推送
"""

from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS
from database import get_recent_data, get_devices, get_latest_data

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
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
