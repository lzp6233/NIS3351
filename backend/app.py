"""
Flask Web 服务器
提供 API 接口

模块化架构：
- routes/air_conditioner.py - 空调模块（温湿度监控与控制）
- routes/lock.py - 智能门锁模块
- routes/lighting.py - 智能灯具模块
- routes/smoke_alarm.py - 烟雾报警器模块
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from config import FLASK_HOST, FLASK_PORT

# 导入各设备模块的路由蓝图
from routes.air_conditioner import air_conditioner_bp
from routes.lock import lock_bp
from routes.lighting import lighting_bp
from routes.smoke_alarm import smoke_alarm_bp

app = Flask(__name__)

# 配置 CORS 以允许来自前端的请求
# 开发环境设置 max_age=0 避免浏览器缓存 CORS 预检请求
CORS(app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    supports_credentials=False,
    max_age=0)

# 添加响应头处理器以确保 CORS 头始终存在
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Accept,Origin,X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Max-Age'] = '0'  # 开发环境禁用缓存
    print(f"[CORS] {request.method} {request.path} - Origin: {request.headers.get('Origin')} - Status: {response.status_code}")
    return response


# 添加 OPTIONS 处理
@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Accept,Origin,X-Requested-With'
        response.headers['Access-Control-Max-Age'] = '0'  # 开发环境禁用缓存
        print(f"[CORS-OPTIONS] {request.path} - Origin: {request.headers.get('Origin')}")
        return response


# 注册各设备模块的蓝图（Blueprint）
# 空调模块 - 负责人：lzp
app.register_blueprint(air_conditioner_bp)

# 智能门锁模块 - 负责人：lsq
app.register_blueprint(lock_bp)

# 全屋灯具控制模块 - 负责人：lzx
app.register_blueprint(lighting_bp)

# 烟雾报警器模块
app.register_blueprint(smoke_alarm_bp)


@app.route("/")
def index():
    """首页 - API 文档"""
    return jsonify({
        "message": "NIS3351 智能家居监控系统 API",
        "version": "1.0",
        "modules": {
            "air_conditioner": {
                "description": "空调模块（温湿度监控与控制）",
                "responsible": "lzp",
                "endpoints": {
                    "/devices": "获取所有设备列表",
                    "/history": "获取历史数据",
                    "/history/<device_id>": "获取指定设备的历史数据",
                    "/latest/<device_id>": "获取指定设备的最新数据"
                }
            },
            "lock": {
                "description": "智能门锁模块",
                "endpoints": {
                    "/locks": "获取所有门锁列表",
                    "/locks/<lock_id>/state": "获取门锁状态",
                    "/locks/<lock_id>/events": "获取门锁事件历史",
                    "/locks/<lock_id>/command": "发送门锁控制命令"
                }
            },
            "lighting": {
                "description": "全屋灯具控制模块",
                "endpoints": {
                    "/lighting": "获取所有灯具列表",
                    "/lighting/<light_id>": "获取灯具状态",
                    "/lighting/<light_id>/control": "控制灯具",
                    "/lighting/<light_id>/events": "获取灯具事件历史",
                    "/lighting/<light_id>/auto-adjust": "智能调节灯具亮度",
                    "/lighting/batch-control": "批量控制多个灯具"
                }
            },
            "smoke_alarm": {
                "description": "烟雾报警器模块",
                "endpoints": {
                    "/smoke_alarms": "获取所有烟雾报警器列表",
                    "/smoke_alarms/<alarm_id>": "获取烟雾报警器状态",
                    "/smoke_alarms/<alarm_id>/test": "启动/停止测试模式",
                    "/smoke_alarms/<alarm_id>/sensitivity": "更新灵敏度设置",
                    "/smoke_alarms/<alarm_id>/events": "获取事件历史",
                    "/smoke_alarms/<alarm_id>/acknowledge": "确认/清除报警"
                }
            }
        }
    })


if __name__ == "__main__":
    print("="*60)
    print("Flask Web 服务器启动 - 模块化架构")
    print("="*60)
    print("已加载模块:")
    print("  ❄️  空调模块 (routes/air_conditioner.py) - 负责人: lzp")
    print("  🔒 智能门锁模块 (routes/lock.py) - 负责人: lsq")
    print("  💡 全屋灯具控制模块 (routes/lighting.py) - 负责人: lzx")
    print("  🚨 烟雾报警器模块 (routes/smoke_alarm.py)")
    print("="*60)
    print("API 端点:")
    print("  空调:")
    print("    GET  /devices              - 获取设备列表")
    print("    GET  /history              - 获取所有历史数据")
    print("    GET  /history/<device_id>  - 获取指定设备历史数据")
    print("    GET  /latest/<device_id>   - 获取指定设备最新数据")
    print("  门锁:")
    print("    GET  /locks                    - 获取门锁列表")
    print("    GET  /locks/<lock_id>/state    - 获取门锁状态")
    print("    GET  /locks/<lock_id>/events   - 获取门锁事件")
    print("    POST /locks/<lock_id>/command  - 发送控制命令")
    # ------------------------------------------------------------------------------------------------------
    print("  灯具:")
    print("    GET  /lighting                 - 获取灯具列表")
    print("    GET  /lighting/<light_id>     - 获取灯具状态")
    print("    POST /lighting/<light_id>/control - 控制灯具")
    print("    POST /lighting/<light_id>/auto-adjust - 智能调节")
    print("    POST /lighting/batch-control   - 批量控制")
    print("  烟雾报警器:")
    print("    GET  /smoke_alarms                      - 获取所有烟雾报警器")
    print("    GET  /smoke_alarms/<alarm_id>           - 获取报警器状态")
    print("    POST /smoke_alarms/<alarm_id>/test      - 启动/停止测试模式")
    print("    PUT  /smoke_alarms/<alarm_id>/sensitivity - 更新灵敏度")
    print("    POST /smoke_alarms/<alarm_id>/acknowledge - 确认/清除报警")
    print("="*60)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
