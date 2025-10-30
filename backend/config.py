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
    try:
        print(f"✓ 已加载配置文件: {env_path}")
    except UnicodeEncodeError:
        print(f"[OK] Config loaded: {env_path}")
except ImportError:
    try:
        print("⚠ 未安装 python-dotenv，使用默认配置")
        print("  提示：运行 'pip install python-dotenv' 来启用 .env 文件支持")
    except UnicodeEncodeError:
        print("[WARNING] python-dotenv not installed, using default config")
        print("  Hint: Run 'pip install python-dotenv' to enable .env file support")
except Exception as e:
    try:
        print(f"⚠ 加载 .env 文件失败: {e}")
    except UnicodeEncodeError:
        print(f"[WARNING] Failed to load .env file: {e}")

# ==================== 数据库配置 ====================
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "smart_home"),
    "user": os.getenv("DB_USER", "opengauss"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "7654"))
}

# 从PINCODE配置文件读取
try:
    from pincode_config import get_pincode
    GLOBAL_PINCODE = get_pincode()
except ImportError:
    GLOBAL_PINCODE = os.getenv("GLOBAL_PINCODE", "041117")

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

# ==================== 模拟器配置 ====================
# 温湿度传感器数据发送间隔（秒）
INTERVAL = int(os.getenv("SENSOR_INTERVAL", "5"))

# 烟雾报警器数据发送间隔（秒）
SMOKE_ALARM_INTERVAL = int(os.getenv("SMOKE_ALARM_INTERVAL", "3"))

# 照明系统配置
# 房间亮度检测间隔（秒）
LIGHTING_CHECK_INTERVAL = int(os.getenv("LIGHTING_CHECK_INTERVAL", "30"))
# 自动开灯的房间亮度阈值（lux）
LIGHTING_BRIGHTNESS_THRESHOLD = float(os.getenv("LIGHTING_BRIGHTNESS_THRESHOLD", "30"))

# 前端静态服务端口
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8000"))

# 要模拟的温湿度传感器设备列表
SENSORS = [
    {
        "device_id": "room1",
        "location": "客厅",
        "topic": "home/room1/temperature_humidity",
        "enabled": True
    },
    {
        "device_id": "room2",
        "location": "卧室",
        "topic": "home/room2/temperature_humidity",
        "enabled": True
    },
]

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
