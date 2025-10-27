#!/usr/bin/env python3
"""
门锁用户初始化脚本
"""

import os
import sys
import base64
import hashlib
import random
import string

# 添加 backend 路径
current_dir = os.path.dirname(__file__)
backend_dir = os.path.join(current_dir, 'backend')
sys.path.insert(0, backend_dir)

from backend.database import create_lock_user, get_connection, DB_TYPE

def generate_fingerprint_data():
    """生成模拟指纹数据（64位随机字符串）"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

def create_sample_face_image(username):
    """创建示例面部图像文件"""
    # 创建用户图像目录
    images_dir = os.path.join(current_dir, 'user_images')
    os.makedirs(images_dir, exist_ok=True)
    
    # 生成一个简单的示例图像（实际应用中应该是真实照片）
    image_path = os.path.join(images_dir, f'{username}_face.jpg')
    
    # 创建一个简单的占位图像文件
    with open(image_path, 'w') as f:
        f.write(f"# 这是 {username} 的面部图像占位符\n")
        f.write(f"# 在实际应用中，这里应该是真实的照片文件\n")
        f.write(f"# 创建时间: {__import__('datetime').datetime.now()}\n")
    
    return image_path

def main():
    print("🔐 初始化门锁用户...")
    
    # 默认用户配置
    users = [
        {
            'username': 'lsqxx2027',
            'password': 'lsqxx2027',
            'pincode': '041117',
            'description': 'lsq'
        }
    ]
    
    for user in users:
        try:
            # 创建面部图像文件
            face_image_path = create_sample_face_image(user['username'])
            
            # 生成指纹数据
            fingerprint_data = generate_fingerprint_data()
            
            # 创建用户
            create_lock_user(
                username=user['username'],
                password=user['password'],
                pincode=user['pincode'],
                face_image_path=face_image_path,
                fingerprint_data=fingerprint_data
            )
            
            print(f"✅ 创建用户: {user['username']}")
            print(f"   - 密码: {user['password']}")
            print(f"   - PIN码: {user['pincode']}")
            print(f"   - 面部图像: {face_image_path}")
            print(f"   - 指纹数据: {fingerprint_data[:16]}...")
            print()
            
        except Exception as e:
            print(f"❌ 创建用户 {user['username']} 失败: {e}")
    
    print("🎉 门锁用户初始化完成！")

if __name__ == "__main__":
    main()
