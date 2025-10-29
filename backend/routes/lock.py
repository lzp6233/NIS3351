"""
智能门锁模块 API 路由
负责人：[门锁模块负责人]
功能：门锁状态管理、开锁/上锁控制、事件记录
"""

from flask import Blueprint, jsonify, request
from database import (
    get_all_locks, get_lock_state, get_lock_events, 
    insert_lock_event, verify_user_password, get_user_face_image,
    get_user_fingerprint_data, get_auto_lock_config, update_auto_lock_config,
    create_lock_user, get_all_lock_users, delete_lock_user, get_connection
)
from config import GLOBAL_PINCODE, DB_TYPE
from mqtt_client import publish_lock_command


def verify_pincode(pin):
    """验证PINCODE是否与全局PINCODE一致"""
    from pincode_config import get_pincode
    current_pincode = get_pincode()
    return str(pin) == str(current_pincode)


def verify_fingerprint_credentials(username, password):
    """验证指纹识别凭据（使用用户名+密码模拟）"""
    import hashlib
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM lock_users WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            )
            return cur.fetchone() is not None
        else:
            stmt = conn.prepare(
                "SELECT id FROM lock_users WHERE username = $1 AND password_hash = $2"
            )
            rows = stmt(username, password_hash)
            for _ in rows:
                return True
            return False
    finally:
        conn.close()


def update_global_pincode(new_pin):
    """更新全局PINCODE配置"""
    from pincode_config import set_pincode
    import config
    
    # 使用新的PINCODE配置系统
    success = set_pincode(new_pin)
    
    if success:
        # 更新config模块中的GLOBAL_PINCODE
        config.GLOBAL_PINCODE = new_pin
        
        # 记录事件
        insert_lock_event('SYSTEM', event_type='pincode_changed', method='ADMIN', 
                         actor='SYSTEM', detail=f'全局PINCODE已更新为: {new_pin}')
        return True
    else:
        raise Exception("PINCODE更新失败")



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
    method = body.get('method')  # PINCODE/FINGERPRINT/FACE/APP/REMOTE/KEY
    actor = body.get('actor')
    pin = body.get('pin')  # 仅当 method=PINCODE 时使用
    username = body.get('username')  # 用户名
    password = body.get('password')  # 密码
    face_image = body.get('face_image')  # 面部图像数据
    fingerprint_data = body.get('fingerprint_data')  # 指纹数据

    if action not in ("lock", "unlock"):
        return jsonify({"error": "invalid action"}), 400
    # 仅支持三种认证方式：PINCODE、指纹、面部。移除 APP/REMOTE/KEY 等方式。
    if method not in ("PINCODE", "FINGERPRINT", "FACE"):
        return jsonify({"error": "invalid method, supported: PINCODE, FINGERPRINT, FACE"}), 400

    # 验证认证方式
    auth_success = False
    auth_detail = ""
    
    if method == "PINCODE":
        if not pin:
            return jsonify({"error": "PINCODE方式需要PIN码"}), 400
        auth_success = verify_pincode(pin)
        auth_detail = "PINCODE认证" + ("成功" if auth_success else "失败")
        
    elif method == "FACE":
        if not face_image:
            return jsonify({"error": "面部识别需要上传面部图像"}), 400
        # 遍历所有用户进行人脸识别验证
        matched_username = verify_face_recognition_all_users(face_image)
        if matched_username:
            auth_success = True
            username = matched_username  # 更新username为匹配到的用户
            auth_detail = f"面部识别成功 - 用户: {username}"
        else:
            auth_success = False
            auth_detail = "面部识别失败 - 未找到匹配的用户"
        
    elif method == "FINGERPRINT":
        if not all([username, password]):
            return jsonify({"error": "指纹识别需要用户名和密码"}), 400
        # 模拟指纹识别验证（使用用户名+密码）
        auth_success = verify_fingerprint_credentials(username, password)
        auth_detail = "指纹识别" + ("成功" if auth_success else "失败")
        
    # 不再支持其他方式，前面已经校验过 method

    if not auth_success:
        # 认证失败，记录事件但不执行命令
        insert_lock_event(lock_id, event_type=f"auth_fail_{action}", method=method, 
                         actor=actor or username, detail=auth_detail)
        return jsonify({"error": "认证失败", "detail": auth_detail}), 401

    # 认证成功，发布到 MQTT
    publish_lock_command(lock_id, action, method=method, actor=actor or username, pin=pin)

    # 记录命令事件
    insert_lock_event(lock_id, event_type=f"cmd_{action}", method=method, 
                     actor=actor or username, detail=f"{auth_detail} - 命令已发送")
    
    # 如果是解锁且启用了自动锁定，设置定时器
    if action == "unlock":
        auto_config = get_auto_lock_config(lock_id)
        if auto_config['auto_lock_enabled']:
            # 这里可以启动一个后台任务来实现自动锁定
            # 为了简化，我们将在模拟器中实现这个逻辑
            pass
    
    return jsonify({"status": "sent", "auth_detail": auth_detail})


def verify_face_recognition_all_users(face_image_data):
    """遍历所有用户进行人脸识别验证，返回匹配的用户名（如果找到）
    使用分数最高的用户，确保分数足够高且与其他用户有明显差距
    """
    try:
        from face_recognition_utils import (
            decode_base64_image, extract_face_features, 
            compare_face_features_with_score, load_image_from_file
        )
        
        # 解码上传的图像并提取特征
        uploaded_image = decode_base64_image(face_image_data)
        if uploaded_image is None:
            print("无法解码上传的图像")
            return None
        
        uploaded_features = extract_face_features(uploaded_image)
        if uploaded_features is None:
            print("无法提取上传图像的特征")
            return None
        
        # 获取所有注册用户
        all_users = get_all_lock_users()
        if not all_users:
            print("数据库中没有任何注册用户")
            return None
        
        # 存储所有用户的匹配分数
        user_scores = []
        
        # 遍历所有用户进行比对
        for username in all_users:
            registered_face_path = get_user_face_image(username)
            if not registered_face_path:
                continue
            
            # 加载注册图像并提取特征
            try:
                registered_image = load_image_from_file(registered_face_path)
                if registered_image is None:
                    continue
                
                registered_features = extract_face_features(registered_image)
                if registered_features is None:
                    continue
                
                # 计算匹配分数
                score = compare_face_features_with_score(uploaded_features, registered_features)
                user_scores.append((username, score))
                print(f"用户 {username} 匹配分数: {score:.3f}")
                
            except Exception as e:
                print(f"比对用户 {username} 时出错: {e}")
                continue
        
        if not user_scores:
            print("没有找到任何有效的用户进行比较")
            return None
        
        # 按分数排序，找出分数最高的用户
        user_scores.sort(key=lambda x: x[1], reverse=True)
        best_username, best_score = user_scores[0]
        
        # 要求最低分数阈值（避免误匹配）
        min_score_threshold = 0.35
        
        # 如果有多个用户，要求最高分数与第二高分数有明显差距（至少0.1）
        if len(user_scores) > 1:
            second_score = user_scores[1][1]
            score_gap = best_score - second_score
            
            if best_score < min_score_threshold:
                print(f"最高分数 {best_score:.3f} 低于阈值 {min_score_threshold}")
                return None
            
            if score_gap < 0.1:
                print(f"最高分数 {best_score:.3f} 与第二高分 {second_score:.3f} 差距太小 ({score_gap:.3f})，可能是误匹配")
                return None
            
            print(f"匹配成功：用户 {best_username} (分数: {best_score:.3f}, 与第二名差距: {score_gap:.3f})")
        else:
            if best_score < min_score_threshold:
                print(f"唯一用户分数 {best_score:.3f} 低于阈值 {min_score_threshold}")
                return None
            print(f"匹配成功：用户 {best_username} (分数: {best_score:.3f})")
        
        return best_username
        
    except Exception as e:
        print(f"人脸识别验证失败: {e}")
        return None


def verify_fingerprint(username, fingerprint_data):
    """模拟指纹识别验证"""
    # 获取用户注册的指纹数据
    registered_fingerprint = get_user_fingerprint_data(username)
    if not registered_fingerprint:
        return False
    
    # 模拟指纹匹配：比较指纹数据的相似度
    # 在实际应用中，这里会使用复杂的指纹识别算法
    try:
        # 简单的模拟：如果提供的指纹数据与注册的指纹数据有80%以上的相似度
        if isinstance(fingerprint_data, str) and isinstance(registered_fingerprint, str):
            # 计算字符串相似度（简化版）
            matches = sum(1 for a, b in zip(fingerprint_data, registered_fingerprint) if a == b)
            similarity = matches / max(len(fingerprint_data), len(registered_fingerprint))
            return similarity > 0.8
        return False
    except:
        return False


@lock_bp.route("/<lock_id>/auto-lock", methods=["GET", "POST"])
def auto_lock_config(lock_id):
    """获取或设置自动锁定配置"""
    if request.method == "GET":
        config = get_auto_lock_config(lock_id)
        return jsonify(config)
    
    elif request.method == "POST":
        body = request.get_json(force=True) or {}
        auto_lock_enabled = body.get('auto_lock_enabled', True)
        auto_lock_delay = body.get('auto_lock_delay', 5)
        
        update_auto_lock_config(lock_id, auto_lock_enabled, auto_lock_delay)
        return jsonify({"status": "updated"})


@lock_bp.route("/users", methods=["GET"])
def list_users():
    """获取所有门锁用户列表（仅返回用户名）"""
    return jsonify({"users": get_all_lock_users()})


@lock_bp.route('/users/<username>', methods=['DELETE'])
def delete_user(username):
    """注销指定用户（需要密码验证）"""
    try:
        # 获取请求体中的密码
        body = {}
        if request.is_json:
            body = request.get_json() or {}
        password = body.get('password')
        
        if not password:
            return jsonify({'error': '注销用户需要提供密码验证'}), 400
        
        # 检查用户是否存在
        users = get_all_lock_users()
        if username not in users:
            return jsonify({'error': '用户不存在'}), 404
        
        # 验证用户密码
        if not verify_user_password(username, password):
            return jsonify({'error': '密码验证失败'}), 401
        
        # 删除用户前清理面部文件与特征缓存
        try:
            import os
            face_path = get_user_face_image(username)
            if face_path and os.path.exists(face_path):
                os.remove(face_path)
            # 删除缓存特征文件（如存在）
            features_dir = os.path.join(os.path.dirname(face_path) if face_path else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'user_images')), 'face_features')
            features_file = os.path.join(features_dir, f"{username}_features.npy")
            if os.path.exists(features_file):
                os.remove(features_file)
        except Exception:
            # 文件清理失败不影响账户删除
            pass

        # 删除用户
        delete_lock_user(username)
        
        # 记录事件
        insert_lock_event('SYSTEM', event_type='user_deleted', method='ADMIN', 
                         actor='SYSTEM', detail=f'用户 {username} 已被注销')
        
        return jsonify({'status': 'deleted', 'username': username})
    except Exception as e:
        return jsonify({'error': f'注销用户失败: {str(e)}'}), 500


@lock_bp.route('/users', methods=['POST'])
def create_user():
    """注册新用户：username, password, (face_image base64), (fingerprint_data)

    根据新需求，全局 PINCODE 由配置决定（GLOBAL_PINCODE），因此在创建用户时将使用该值。
    """
    body = request.get_json(force=True) or {}
    username = body.get('username')
    password = body.get('password')
    face_image_b64 = body.get('face_image')
    fingerprint_data = body.get('fingerprint_data')

    if not username or not password:
        return jsonify({'error': 'username and password are required'}), 400

    # 保存面部图像到 user_images 目录（如果提供）
    face_image_path = None
    if face_image_b64:
        try:
            import os, base64
            project_root = os.path.dirname(os.path.dirname(__file__))
            images_dir = os.path.join(project_root, '..', 'user_images')
            # normalize
            images_dir = os.path.abspath(os.path.join(project_root, '..', 'user_images'))
            os.makedirs(images_dir, exist_ok=True)
            filename = f"{username}_face_{int(__import__('time').time())}.jpg"
            path = os.path.join(images_dir, filename)
            with open(path, 'wb') as f:
                f.write(base64.b64decode(face_image_b64))
            face_image_path = path
        except Exception as e:
            return jsonify({'error': f'failed to save face image: {e}'}), 500

    try:
        # 使用全局 PINCODE 存储到用户表中（所有用户共享同一 PIN）
        create_lock_user(username=username, password=password,
                         face_image_path=face_image_path, fingerprint_data=fingerprint_data)
        return jsonify({'status': 'created', 'username': username})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lock_bp.route('/pincode', methods=['POST'])
def change_pincode():
    """修改全局PINCODE：需要验证当前PINCODE，然后设置新的PINCODE"""
    body = request.get_json(force=True) or {}
    current_pin = body.get('current_pin')
    new_pin = body.get('new_pin')

    if not current_pin or not new_pin:
        return jsonify({'error': 'current_pin and new_pin are required'}), 400

    # 验证当前PINCODE
    if not verify_pincode(current_pin):
        return jsonify({'error': '当前PINCODE不正确'}), 401

    # 验证新PINCODE格式
    if len(new_pin) < 4:
        return jsonify({'error': '新PINCODE长度至少4位'}), 400

    try:
        # 更新全局PINCODE配置
        update_global_pincode(new_pin)
        return jsonify({'status': 'updated', 'message': 'PINCODE修改成功'})
    except Exception as e:
        return jsonify({'error': f'修改PINCODE失败: {str(e)}'}), 500



