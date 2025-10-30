"""
房间管理模块 API 路由
功能：房间信息管理、设备关联查询
"""

from flask import Blueprint, jsonify, request
import sys
import os

# 添加当前目录到路径以便导入 database_enhanced
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database_enhanced import get_all_rooms, get_room_by_id, create_room, update_room, delete_room

# 创建蓝图
rooms_bp = Blueprint('rooms', __name__, url_prefix='/rooms')


@rooms_bp.route("", methods=["GET"])
def list_rooms():
    """获取所有房间列表"""
    try:
        rooms = get_all_rooms()
        return jsonify({
            "success": True,
            "count": len(rooms),
            "rooms": rooms
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@rooms_bp.route("", methods=["POST"])
def create_new_room():
    """创建新房间

    请求体示例:
    {
        "room_id": "study_room",
        "room_name": "书房",
        "floor": 2,
        "area": 15.5,
        "description": "安静的学习空间"
    }
    """
    try:
        data = request.get_json()

        # 验证必填字段
        required = ['room_id', 'room_name']
        for field in required:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400

        # 检查房间是否已存在
        existing = get_room_by_id(data['room_id'])
        if existing:
            return jsonify({
                "success": False,
                "error": "Room with this ID already exists"
            }), 409

        success = create_room(
            room_id=data['room_id'],
            room_name=data['room_name'],
            floor=data.get('floor', 1),
            area=data.get('area'),
            description=data.get('description')
        )

        if success:
            return jsonify({
                "success": True,
                "message": "Room created successfully",
                "room_id": data['room_id']
            }), 201
        else:
            return jsonify({
                "success": False,
                "error": "Failed to create room"
            }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@rooms_bp.route("/<room_id>", methods=["GET"])
def room_detail(room_id):
    """获取房间详情及关联的所有设备"""
    try:
        room = get_room_by_id(room_id)
        if room:
            return jsonify({
                "success": True,
                "room": room
            })
        return jsonify({
            "success": False,
            "error": "房间未找到"
        }), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@rooms_bp.route("/<room_id>", methods=["PUT"])
def update_existing_room(room_id):
    """更新房间信息

    可更新字段: room_name, floor, area, description
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        # 检查房间是否存在
        existing = get_room_by_id(room_id)
        if not existing:
            return jsonify({
                "success": False,
                "error": "Room not found"
            }), 404

        success = update_room(room_id, **data)

        if success:
            return jsonify({
                "success": True,
                "message": "Room updated successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "No changes made or room not found"
            }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@rooms_bp.route("/<room_id>", methods=["DELETE"])
def remove_room(room_id):
    """删除房间"""
    try:
        # 检查房间是否存在
        existing = get_room_by_id(room_id)
        if not existing:
            return jsonify({
                "success": False,
                "error": "Room not found"
            }), 404

        # 检查是否有设备关联到此房间
        if existing.get('smoke_alarms') and len(existing['smoke_alarms']) > 0:
            return jsonify({
                "success": False,
                "error": "Cannot delete room with associated devices",
                "device_count": len(existing['smoke_alarms'])
            }), 409

        success = delete_room(room_id)

        if success:
            return jsonify({
                "success": True,
                "message": "Room deleted successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to delete room"
            }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@rooms_bp.route("/<room_id>/devices", methods=["GET"])
def room_devices(room_id):
    """获取房间的所有设备统计"""
    try:
        room = get_room_by_id(room_id)
        if not room:
            return jsonify({"error": "房间未找到"}), 404

        # 返回设备摘要
        device_summary = {
            "room_id": room['room_id'],
            "room_name": room['room_name'],
            "smoke_alarms_count": len(room.get('smoke_alarms', [])),
            "smoke_alarms": room.get('smoke_alarms', []),
            # 可以扩展添加其他设备类型
        }

        return jsonify(device_summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
