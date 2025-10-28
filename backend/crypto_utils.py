"""
加密工具模块
用于加密存储敏感信息如密码、PINCODE等
"""

import hashlib
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 生成或加载加密密钥
def get_or_create_key():
    """获取或创建加密密钥"""
    key_file = os.path.join(os.path.dirname(__file__), '..', 'encryption.key')
    
    if os.path.exists(key_file):
        # 从文件读取密钥
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        # 生成新密钥
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        # 设置文件权限，只有所有者可读写
        os.chmod(key_file, 0o600)
        return key

# 全局加密器实例
_fernet = None

def get_fernet():
    """获取Fernet加密器实例"""
    global _fernet
    if _fernet is None:
        key = get_or_create_key()
        _fernet = Fernet(key)
    return _fernet

def encrypt_password(password):
    """加密密码"""
    if not password:
        return None
    
    fernet = get_fernet()
    # 将密码编码为字节，然后加密
    encrypted_password = fernet.encrypt(password.encode('utf-8'))
    # 返回base64编码的加密数据
    return base64.b64encode(encrypted_password).decode('utf-8')

def decrypt_password(encrypted_password):
    """解密密码"""
    if not encrypted_password:
        return None
    
    try:
        fernet = get_fernet()
        # 从base64解码
        encrypted_data = base64.b64decode(encrypted_password.encode('utf-8'))
        # 解密
        decrypted_data = fernet.decrypt(encrypted_data)
        return decrypted_data.decode('utf-8')
    except Exception as e:
        # print(f"解密密码失败: {e}")
        return None

def hash_password(password):
    """使用SHA-256哈希密码（用于验证）"""
    if not password:
        return None
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password, hashed_password):
    """验证密码"""
    if not password or not hashed_password:
        return False
    return hash_password(password) == hashed_password

def encrypt_pincode(pincode):
    """加密PINCODE"""
    return encrypt_password(str(pincode))

def decrypt_pincode(encrypted_pincode):
    """解密PINCODE"""
    return decrypt_password(encrypted_pincode)

# 管理员密码验证
ADMIN_PASSWORD_HASH = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # "password"的SHA-256哈希

def verify_admin_password(password):
    """验证管理员密码"""
    return verify_password(password, ADMIN_PASSWORD_HASH)
