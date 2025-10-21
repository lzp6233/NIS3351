"""
配置文件：数据库和MQTT配置
从环境变量或 .env 文件读取配置
"""

import os
from pathlib import Path

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    # 加载项目根目录的 .env 文件
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"✓ 已加载配置文件: {env_path}")
except ImportError:
    print("⚠ 未安装 python-dotenv，使用默认配置")
    print("  提示：运行 'pip install python-dotenv' 来启用 .env 文件支持")
except Exception as e:
    print(f"⚠ 加载 .env 文件失败: {e}")

# ==================== 数据库配置 ====================
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "smart_home"),
    "user": os.getenv("DB_USER", "opengauss"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "7654"))
}


# 数据库类型：'opengauss' 或 'sqlite'（本地默认 sqlite，便于零依赖运行）
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
# 当使用 sqlite 时，DB_PATH 指向数据库文件（相对或绝对路径）
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / 'data.sqlite3'))

# ==================== MQTT 配置 ====================
MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "home/+/temperature_humidity")

# ==================== 应用配置 ====================
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ==================== 使用说明 ====================
"""
使用 .env 文件配置：

1. 创建 .env 文件：
   cp .env.example .env

2. 编辑 .env 文件，设置你的配置：
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_PORT=7654
   ...

3. 安装 python-dotenv：
   pip install python-dotenv

4. 配置会自动从 .env 文件加载

优势：
- ✅ 敏感信息不会提交到 Git
- ✅ 不同环境使用不同的 .env 文件
- ✅ 配置修改无需改动代码
"""
