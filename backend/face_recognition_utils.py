"""
人脸识别工具模块
使用OpenCV和PIL实现基础的人脸识别功能
"""

import cv2
import numpy as np
import base64
import os
from PIL import Image
import io
import hashlib

def decode_base64_image(base64_data):
    """将base64编码的图像数据解码为OpenCV图像"""
    try:
        # 解码base64数据
        image_data = base64.b64decode(base64_data)
        
        # 转换为PIL图像
        pil_image = Image.open(io.BytesIO(image_data))
        
        # 转换为RGB格式（如果需要）
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # 转换为OpenCV格式
        opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        return opencv_image
    except Exception as e:
        print(f"解码图像失败: {e}")
        return None

def load_image_from_file(file_path):
    """从文件加载图像"""
    try:
        if not os.path.exists(file_path):
            return None
        
        # 使用OpenCV加载图像
        image = cv2.imread(file_path)
        return image
    except Exception as e:
        print(f"加载图像失败: {e}")
        return None

def compute_lbp_features(image):
    """计算LBP (Local Binary Pattern) 特征"""
    try:
        # 简化的LBP实现
        rows, cols = image.shape
        lbp = np.zeros_like(image)
        
        for i in range(1, rows-1):
            for j in range(1, cols-1):
                center = image[i, j]
                code = 0
                code |= (image[i-1, j-1] >= center) << 7
                code |= (image[i-1, j] >= center) << 6
                code |= (image[i-1, j+1] >= center) << 5
                code |= (image[i, j+1] >= center) << 4
                code |= (image[i+1, j+1] >= center) << 3
                code |= (image[i+1, j] >= center) << 2
                code |= (image[i+1, j-1] >= center) << 1
                code |= (image[i, j-1] >= center) << 0
                lbp[i, j] = code
        
        # 计算LBP直方图
        hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
        return hist.astype(np.float32)
    except Exception as e:
        print(f"计算LBP特征失败: {e}")
        return None

def compute_image_hash(image):
    """计算图像感知哈希"""
    try:
        # 调整图像大小到8x8
        resized = cv2.resize(image, (8, 8))
        
        # 计算平均灰度值
        avg = np.mean(resized)
        
        # 生成哈希
        hash_bits = []
        for i in range(8):
            for j in range(8):
                hash_bits.append(1 if resized[i, j] > avg else 0)
        
        # 转换为字符串
        hash_str = ''.join(map(str, hash_bits))
        return hash_str
    except Exception as e:
        print(f"计算图像哈希失败: {e}")
        return None

def hamming_distance(hash1, hash2):
    """计算两个哈希之间的汉明距离"""
    if len(hash1) != len(hash2):
        return float('inf')
    
    distance = 0
    for i in range(len(hash1)):
        if hash1[i] != hash2[i]:
            distance += 1
    
    return distance

def extract_face_features(image):
    """提取人脸特征（改进版）"""
    try:
        # 转换为灰度图像
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用Haar级联分类器检测人脸
        try:
            # 尝试不同的路径来找到Haar级联文件
            cascade_paths = [
                '/home/NIS3351/haarcascade_frontalface_default.xml',
                '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
                '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
                'haarcascade_frontalface_default.xml'
            ]
            
            # 尝试使用cv2.data（如果可用）
            try:
                cascade_paths.insert(0, cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            except AttributeError:
                pass
            
            face_cascade = None
            for path in cascade_paths:
                try:
                    face_cascade = cv2.CascadeClassifier(path)
                    if not face_cascade.empty():
                        print(f"成功加载人脸检测器: {path}")
                        break
                except:
                    continue
            
            if face_cascade is None or face_cascade.empty():
                print("无法加载人脸检测级联分类器，使用简化检测")
                # 使用简化的检测方法：假设图像中心区域是人脸
                h, w = gray.shape
                center_x, center_y = w // 2, h // 2
                face_size = min(w, h) // 3
                faces = [(center_x - face_size//2, center_y - face_size//2, face_size, face_size)]
            else:
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
        except Exception as e:
            print(f"人脸检测失败，使用简化方法: {e}")
            # 使用简化的检测方法
            h, w = gray.shape
            center_x, center_y = w // 2, h // 2
            face_size = min(w, h) // 3
            faces = [(center_x - face_size//2, center_y - face_size//2, face_size, face_size)]
        
        if len(faces) == 0:
            print("未检测到人脸，人脸识别失败")
            return None
        
        # 获取最大的人脸
        largest_face = max(faces, key=lambda x: x[2] * x[3])
        x, y, w, h = largest_face
        
        # 提取人脸区域，并添加一些边距
        margin = int(min(w, h) * 0.1)  # 10%的边距
        x_start = max(0, x - margin)
        y_start = max(0, y - margin)
        x_end = min(gray.shape[1], x + w + margin)
        y_end = min(gray.shape[0], y + h + margin)
        
        face_roi = gray[y_start:y_end, x_start:x_end]
        
        # 调整大小到标准尺寸
        face_resized = cv2.resize(face_roi, (128, 128))
        
        # 计算多种特征以提高识别准确性
        
        # 1. 直方图特征
        hist = cv2.calcHist([face_resized], [0], None, [256], [0, 256])
        hist_normalized = cv2.normalize(hist, hist).flatten()
        
        # 2. ORB 描述子
        orb = cv2.ORB_create(nfeatures=500)
        keypoints, descriptors = orb.detectAndCompute(face_resized, None)
        
        # 3. LBP (Local Binary Pattern) 特征
        lbp_features = compute_lbp_features(face_resized)
        
        # 4. 图像哈希特征
        image_hash = compute_image_hash(face_resized)
        
        return {
            'hist': hist_normalized,
            'keypoints': keypoints,
            'descriptors': descriptors,
            'lbp': lbp_features,
            'hash': image_hash,
            'face_detected': True
        }
    except Exception as e:
        print(f"提取人脸特征失败: {e}")
        return None

def compare_face_features(features1, features2, threshold=0.5):
    """比较两个人脸特征（多特征融合）"""
    try:
        if features1 is None or features2 is None:
            return False
        
        # 检查是否检测到人脸
        if not features1.get('face_detected', False) or not features2.get('face_detected', False):
            print("至少有一张图像未检测到人脸")
            return False
        
        match_scores = []
        
        # 1. ORB 描述子匹配（权重最高）
        desc1 = features1.get('descriptors')
        desc2 = features2.get('descriptors')
        
        if desc1 is not None and desc2 is not None and len(desc1) > 0 and len(desc2) > 0:
            try:
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
                matches = bf.knnMatch(desc1, desc2, k=2)
                
                good_matches = []
                for m_n in matches:
                    if len(m_n) == 2:
                        m, n = m_n
                        if m.distance < 0.75 * n.distance:
                            good_matches.append(m)
                
                # 计算ORB匹配分数
                orb_score = len(good_matches) / max(len(desc1), len(desc2))
                match_scores.append(('ORB', orb_score, 0.4))  # 权重40%
                print(f"ORB匹配分数: {orb_score:.3f}")
            except Exception as e:
                print(f"ORB匹配失败: {e}")
        
        # 2. 直方图相关系数比较
        h1 = features1.get('hist')
        h2 = features2.get('hist')
        if h1 is not None and h2 is not None:
            hist_correlation = cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL)
            match_scores.append(('Histogram', hist_correlation, 0.3))  # 权重30%
            print(f"直方图相关系数: {hist_correlation:.3f}")
        
        # 3. LBP特征比较
        lbp1 = features1.get('lbp')
        lbp2 = features2.get('lbp')
        if lbp1 is not None and lbp2 is not None:
            lbp_correlation = cv2.compareHist(lbp1, lbp2, cv2.HISTCMP_CORREL)
            match_scores.append(('LBP', lbp_correlation, 0.2))  # 权重20%
            print(f"LBP相关系数: {lbp_correlation:.3f}")
        
        # 4. 图像哈希比较
        hash1 = features1.get('hash')
        hash2 = features2.get('hash')
        if hash1 is not None and hash2 is not None:
            hamming_dist = hamming_distance(hash1, hash2)
            # 将汉明距离转换为相似度分数（0-1）
            hash_similarity = max(0, 1 - hamming_dist / 64.0)  # 64位哈希
            match_scores.append(('Hash', hash_similarity, 0.1))  # 权重10%
            print(f"哈希相似度: {hash_similarity:.3f} (汉明距离: {hamming_dist})")
        
        if not match_scores:
            print("没有可用的特征进行比较")
            return False
        
        # 计算加权平均分数
        total_weight = sum(weight for _, _, weight in match_scores)
        weighted_score = sum(score * weight for _, score, weight in match_scores) / total_weight
        
        print(f"综合匹配分数: {weighted_score:.3f} (阈值: {threshold})")
        
        # 判断是否匹配
        is_match = weighted_score > threshold
        
        # 额外检查：如果ORB分数特别高，即使总分略低于阈值也认为匹配
        if not is_match and len(match_scores) > 0:
            orb_scores = [score for name, score, _ in match_scores if name == 'ORB']
            if orb_scores and orb_scores[0] > 0.3:  # ORB分数超过0.3
                print("ORB分数较高，调整匹配结果")
                is_match = True
        
        return is_match
        
    except Exception as e:
        print(f"比较人脸特征失败: {e}")
        return False

def verify_face_recognition(username, face_image_data, registered_face_path):
    """验证人脸识别"""
    try:
        # 解码上传的图像
        uploaded_image = decode_base64_image(face_image_data)
        if uploaded_image is None:
            return False
        
        # 加载注册的图像
        registered_image = load_image_from_file(registered_face_path)
        if registered_image is None:
            return False
        
        # 提取特征
        uploaded_features = extract_face_features(uploaded_image)
        registered_features = extract_face_features(registered_image)

        if uploaded_features is None or registered_features is None:
            return False

        # 首先确保两张图像都检测到人脸（至少提取到描述子或直方图）
        is_match = compare_face_features(uploaded_features, registered_features)
        return bool(is_match)
    except Exception as e:
        print(f"人脸识别验证失败: {e}")
        return False

def save_face_features(username, face_image_data, face_image_path):
    """保存人脸特征到文件（用于缓存）"""
    try:
        # 解码图像
        image = decode_base64_image(face_image_data)
        if image is None:
            return False
        
        # 提取特征
        features = extract_face_features(image)
        if features is None:
            return False
        
        # 保存特征到文件
        features_dir = os.path.join(os.path.dirname(face_image_path), 'face_features')
        os.makedirs(features_dir, exist_ok=True)
        
        features_file = os.path.join(features_dir, f"{username}_features.npy")
        np.save(features_file, features)
        
        return True
    except Exception as e:
        print(f"保存人脸特征失败: {e}")
        return False

def load_face_features(username, face_image_path):
    """加载人脸特征"""
    try:
        features_dir = os.path.join(os.path.dirname(face_image_path), 'face_features')
        features_file = os.path.join(features_dir, f"{username}_features.npy")
        
        if os.path.exists(features_file):
            return np.load(features_file)
        return None
    except Exception as e:
        print(f"加载人脸特征失败: {e}")
        return None
