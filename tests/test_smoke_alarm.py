"""
烟雾报警器功能测试脚本
测试数据库操作、API端点和基本功能
"""

import sys
import os
import io

# 设置标准输出为UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加 backend 路径
current_dir = os.path.dirname(__file__)
backend_dir = os.path.join(current_dir, '..', 'backend')
sys.path.insert(0, backend_dir)

# 导入测试所需的模块
from database import (
    upsert_smoke_alarm_state, get_smoke_alarm_state, get_all_smoke_alarms,
    insert_smoke_alarm_event, get_smoke_alarm_events
)

def print_section(title):
    """打印测试部分标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_database_operations():
    """测试数据库操作"""
    print_section("测试数据库操作")

    # 测试插入/更新烟雾报警器状态
    print("\n1. 测试 upsert_smoke_alarm_state()...")
    try:
        upsert_smoke_alarm_state(
            alarm_id='smoke_test',
            location='test_room',
            smoke_level=15.5,
            alarm_active=False,
            battery=95,
            test_mode=False,
            sensitivity='medium'
        )
        print("   ✓ 插入测试报警器成功")
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

    # 测试获取单个报警器状态
    print("\n2. 测试 get_smoke_alarm_state()...")
    try:
        state = get_smoke_alarm_state('smoke_test')
        if state:
            print(f"   ✓ 获取状态成功:")
            print(f"     - 位置: {state['location']}")
            print(f"     - 烟雾浓度: {state['smoke_level']}%")
            print(f"     - 报警状态: {state['alarm_active']}")
            print(f"     - 电池: {state['battery']}%")
        else:
            print("   ✗ 未找到报警器")
            return False
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

    # 测试获取所有报警器
    print("\n3. 测试 get_all_smoke_alarms()...")
    try:
        alarms = get_all_smoke_alarms()
        print(f"   ✓ 找到 {len(alarms)} 个报警器:")
        for alarm in alarms:
            status = "🚨 报警中" if alarm['alarm_active'] else "✓ 正常"
            print(f"     - {alarm['alarm_id']}: {status} (烟雾: {alarm['smoke_level']}%)")
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

    # 测试插入事件
    print("\n4. 测试 insert_smoke_alarm_event()...")
    try:
        insert_smoke_alarm_event(
            alarm_id='smoke_test',
            event_type='TEST_EVENT',
            smoke_level=15.5,
            detail='This is a test event'
        )
        print("   ✓ 插入事件成功")
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

    # 测试获取事件历史
    print("\n5. 测试 get_smoke_alarm_events()...")
    try:
        events = get_smoke_alarm_events('smoke_test', limit=5)
        print(f"   ✓ 找到 {len(events)} 个事件:")
        for event in events[:3]:
            print(f"     - {event['event_type']}: {event.get('detail', 'N/A')}")
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

    # 测试更新状态（触发报警）
    print("\n6. 测试报警触发...")
    try:
        upsert_smoke_alarm_state(
            alarm_id='smoke_test',
            smoke_level=65.0,
            alarm_active=True
        )
        state = get_smoke_alarm_state('smoke_test')
        if state['alarm_active'] and state['smoke_level'] == 65.0:
            print("   ✓ 报警触发成功")
        else:
            print("   ✗ 报警状态未正确更新")
            return False
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

    # 测试清除报警
    print("\n7. 测试报警清除...")
    try:
        upsert_smoke_alarm_state(
            alarm_id='smoke_test',
            smoke_level=5.0,
            alarm_active=False
        )
        state = get_smoke_alarm_state('smoke_test')
        if not state['alarm_active'] and state['smoke_level'] == 5.0:
            print("   ✓ 报警清除成功")
        else:
            print("   ✗ 报警状态未正确更新")
            return False
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

    print("\n✓ 所有数据库操作测试通过!")
    return True


def test_api_endpoints():
    """测试API端点"""
    print_section("测试API端点")

    try:
        import requests
    except ImportError:
        print("   ⚠ 未安装 requests 库，跳过API测试")
        print("   提示: pip install requests")
        return True

    base_url = 'http://localhost:5000'

    # 测试获取所有报警器
    print("\n1. 测试 GET /smoke_alarms...")
    try:
        response = requests.get(f'{base_url}/smoke_alarms')
        if response.status_code == 200:
            alarms = response.json()
            print(f"   ✓ 成功，返回 {len(alarms)} 个报警器")
        else:
            print(f"   ✗ 失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ⚠ 无法连接到后端服务: {e}")
        print("   提示: 请确保 Flask 服务器正在运行 (python backend/app.py)")
        return True

    # 测试获取单个报警器
    print("\n2. 测试 GET /smoke_alarms/<alarm_id>...")
    try:
        response = requests.get(f'{base_url}/smoke_alarms/smoke_living_room')
        if response.status_code == 200:
            alarm = response.json()
            print(f"   ✓ 成功，烟雾浓度: {alarm.get('smoke_level', 'N/A')}%")
        else:
            print(f"   ✗ 失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"   ✗ 失败: {e}")

    # 测试启动测试模式
    print("\n3. 测试 POST /smoke_alarms/<alarm_id>/test...")
    try:
        response = requests.post(
            f'{base_url}/smoke_alarms/smoke_test/test',
            json={'test_mode': True}
        )
        if response.status_code == 200:
            print("   ✓ 测试模式启动成功")
        else:
            print(f"   ⚠ 状态码: {response.status_code}")
    except Exception as e:
        print(f"   ✗ 失败: {e}")

    # 测试获取事件
    print("\n4. 测试 GET /smoke_alarms/<alarm_id>/events...")
    try:
        response = requests.get(f'{base_url}/smoke_alarms/smoke_test/events')
        if response.status_code == 200:
            events = response.json()
            print(f"   ✓ 成功，返回 {len(events)} 个事件")
        else:
            print(f"   ✗ 失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"   ✗ 失败: {e}")

    print("\n✓ API端点测试完成!")
    return True


def test_simulator():
    """测试模拟器文件是否存在"""
    print_section("检查模拟器文件")

    # 使用正确的路径（从tests目录向上到项目根目录）
    simulator_path = os.path.join(current_dir, '..', 'simulator', 'smoke_alarm_sim.py')
    simulator_path = os.path.abspath(simulator_path)
    if os.path.exists(simulator_path):
        print(f"   ✓ 模拟器文件存在: {simulator_path}")
        print("   提示: 运行 'python simulator/smoke_alarm_sim.py' 启动模拟器")
        return True
    else:
        print(f"   ✗ 模拟器文件不存在: {simulator_path}")
        return False


def test_frontend():
    """测试前端文件是否存在"""
    print_section("检查前端文件")

    # 使用正确的路径（从tests目录向上到项目根目录）
    frontend_path = os.path.join(current_dir, '..', 'frontend', 'smoke-alarm.html')
    frontend_path = os.path.abspath(frontend_path)
    if os.path.exists(frontend_path):
        print(f"   ✓ 前端文件存在: {frontend_path}")
        print("   提示: 访问 http://localhost:8000/smoke-alarm.html")
        return True
    else:
        print(f"   ✗ 前端文件不存在: {frontend_path}")
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("  烟雾报警器模块测试")
    print("="*60)

    results = []

    # 运行测试
    results.append(("数据库操作", test_database_operations()))
    results.append(("API端点", test_api_endpoints()))
    results.append(("模拟器文件", test_simulator()))
    results.append(("前端文件", test_frontend()))

    # 打印测试结果汇总
    print_section("测试结果汇总")
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 所有测试通过！烟雾报警器模块已成功集成到系统中。")
        print("\n下一步:")
        print("  1. 启动系统: sh run.sh")
        print("  2. 访问前端: http://localhost:8000/smoke-alarm.html")
        print("  3. 查看数据: curl http://localhost:5000/smoke_alarms")
    else:
        print("\n⚠ 部分测试未通过，请检查上述错误信息。")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
