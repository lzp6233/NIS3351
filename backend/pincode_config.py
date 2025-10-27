"""
PINCODE配置文件
用于存储和管理全局PINCODE
"""

import os
import json
from pathlib import Path

# PINCODE配置文件路径
PINCODE_CONFIG_FILE = Path(__file__).parent.parent / 'pincode.json'

def get_pincode():
    """获取当前PINCODE"""
    try:
        if PINCODE_CONFIG_FILE.exists():
            with open(PINCODE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('pincode', '041117')
        else:
            # 如果文件不存在，创建默认配置
            set_pincode('041117')
            return '041117'
    except Exception as e:
        print(f"读取PINCODE配置失败: {e}")
        return '041117'

def set_pincode(new_pincode):
    """设置新的PINCODE"""
    try:
        config = {
            'pincode': new_pincode,
            'updated_at': __import__('datetime').datetime.now().isoformat()
        }
        
        # 确保目录存在
        PINCODE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入配置文件
        with open(PINCODE_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"PINCODE已更新为: {new_pincode}")
        return True
    except Exception as e:
        print(f"设置PINCODE失败: {e}")
        return False

def get_pincode_info():
    """获取PINCODE配置信息"""
    try:
        if PINCODE_CONFIG_FILE.exists():
            with open(PINCODE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {
                    'pincode': config.get('pincode', '041117'),
                    'updated_at': config.get('updated_at', 'unknown')
                }
        else:
            return {
                'pincode': '041117',
                'updated_at': 'default'
            }
    except Exception as e:
        print(f"读取PINCODE信息失败: {e}")
        return {
            'pincode': '041117',
            'updated_at': 'error'
        }
