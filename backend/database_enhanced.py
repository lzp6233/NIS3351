"""
数据库增强操作模块
支持烟雾报警器模块的增强功能：
- 房间管理
- 自动化响应规则
- 用户通知配置
- 设备维护记录
- 报警确认系统
- 统计分析
"""

import json
from datetime import date, datetime
from database import get_connection, DB_TYPE


# ==================== 房间管理数据库操作 ====================

def get_all_rooms():
    """获取所有房间列表"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                SELECT room_id, room_name, floor, area, description, created_at
                FROM rooms
                ORDER BY floor, room_id
            """)
            rows = cur.fetchall()
            return [{
                'room_id': r[0],
                'room_name': r[1],
                'floor': r[2],
                'area': r[3],
                'description': r[4],
                'created_at': r[5]
            } for r in rows]
        else:
            stmt = conn.prepare("""
                SELECT room_id, room_name, floor, area, description, created_at
                FROM rooms
                ORDER BY floor, room_id
            """)
            rows = stmt()
            result = []
            for r in rows:
                result.append({
                    'room_id': r[0],
                    'room_name': r[1],
                    'floor': r[2],
                    'area': r[3],
                    'description': r[4],
                    'created_at': r[5].isoformat() if r[5] else None
                })
            return result
    finally:
        conn.close()


def get_room_by_id(room_id):
    """获取房间详情及关联的所有设备"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            # 获取房间信息
            cur.execute("""
                SELECT room_id, room_name, floor, area, description, created_at
                FROM rooms WHERE room_id = ?
            """, (room_id,))
            row = cur.fetchone()
            if not row:
                return None

            room = {
                'room_id': row[0],
                'room_name': row[1],
                'floor': row[2],
                'area': row[3],
                'description': row[4],
                'created_at': row[5]
            }

            # 获取该房间的烟雾报警器
            cur.execute("""
                SELECT alarm_id, smoke_level, alarm_active, battery
                FROM smoke_alarm_state WHERE room_id = ?
            """, (room_id,))
            room['smoke_alarms'] = [{
                'alarm_id': r[0],
                'smoke_level': r[1],
                'alarm_active': bool(r[2]),
                'battery': r[3]
            } for r in cur.fetchall()]

            return room
        else:
            # openGauss implementation
            stmt = conn.prepare("""
                SELECT room_id, room_name, floor, area, description, created_at
                FROM rooms WHERE room_id = $1
            """)
            rows = stmt(room_id)
            room = None
            for r in rows:
                room = {
                    'room_id': r[0],
                    'room_name': r[1],
                    'floor': r[2],
                    'area': r[3],
                    'description': r[4],
                    'created_at': r[5].isoformat() if r[5] else None
                }
                break

            if not room:
                return None

            stmt = conn.prepare("""
                SELECT alarm_id, smoke_level, alarm_active, battery
                FROM smoke_alarm_state WHERE room_id = $1
            """)
            rows = stmt(room_id)
            room['smoke_alarms'] = []
            for r in rows:
                room['smoke_alarms'].append({
                    'alarm_id': r[0],
                    'smoke_level': r[1],
                    'alarm_active': bool(r[2]),
                    'battery': r[3]
                })

            return room
    finally:
        conn.close()


# ==================== 自动化响应规则数据库操作 ====================

def get_all_response_rules(enabled_only=False):
    """获取所有自动化响应规则"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            sql = """
                SELECT rule_id, rule_name, alarm_id, room_id, trigger_condition,
                       condition_value, action_type, action_target, action_params,
                       enabled, priority, created_at, updated_at
                FROM smoke_alarm_response_rules
            """
            if enabled_only:
                sql += " WHERE enabled = 1"
            sql += " ORDER BY priority DESC, created_at DESC"

            cur.execute(sql)
            rows = cur.fetchall()
            return [{
                'rule_id': r[0],
                'rule_name': r[1],
                'alarm_id': r[2],
                'room_id': r[3],
                'trigger_condition': r[4],
                'condition_value': r[5],
                'action_type': r[6],
                'action_target': r[7],
                'action_params': json.loads(r[8]) if r[8] else {},
                'enabled': bool(r[9]),
                'priority': r[10],
                'created_at': r[11],
                'updated_at': r[12]
            } for r in rows]
        else:
            sql = """
                SELECT rule_id, rule_name, alarm_id, room_id, trigger_condition,
                       condition_value, action_type, action_target, action_params,
                       enabled, priority, created_at, updated_at
                FROM smoke_alarm_response_rules
            """
            if enabled_only:
                sql += " WHERE enabled = true"
            sql += " ORDER BY priority DESC, created_at DESC"

            stmt = conn.prepare(sql)
            rows = stmt()
            result = []
            for r in rows:
                result.append({
                    'rule_id': r[0],
                    'rule_name': r[1],
                    'alarm_id': r[2],
                    'room_id': r[3],
                    'trigger_condition': r[4],
                    'condition_value': r[5],
                    'action_type': r[6],
                    'action_target': r[7],
                    'action_params': json.loads(r[8]) if r[8] else {},
                    'enabled': bool(r[9]),
                    'priority': r[10],
                    'created_at': r[11].isoformat() if r[11] else None,
                    'updated_at': r[12].isoformat() if r[12] else None
                })
            return result
    finally:
        conn.close()


def create_response_rule(rule_name, alarm_id=None, room_id=None, trigger_condition=None,
                        condition_value=None, action_type=None, action_target=None,
                        action_params=None, enabled=True, priority=0):
    """创建新的自动化响应规则"""
    conn = get_connection()
    try:
        params_str = json.dumps(action_params) if action_params else None

        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO smoke_alarm_response_rules
                (rule_name, alarm_id, room_id, trigger_condition, condition_value,
                 action_type, action_target, action_params, enabled, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rule_name, alarm_id, room_id, trigger_condition, condition_value,
                  action_type, action_target, params_str, 1 if enabled else 0, priority))
            conn.commit()
            return cur.lastrowid
        else:
            stmt = conn.prepare("""
                INSERT INTO smoke_alarm_response_rules
                (rule_name, alarm_id, room_id, trigger_condition, condition_value,
                 action_type, action_target, action_params, enabled, priority, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
                RETURNING rule_id
            """)
            rows = stmt(rule_name, alarm_id, room_id, trigger_condition, condition_value,
                       action_type, action_target, params_str, enabled, priority)
            for row in rows:
                return row[0]
    finally:
        conn.close()


def update_response_rule(rule_id, **kwargs):
    """更新自动化响应规则"""
    conn = get_connection()
    try:
        updates = []
        values = []

        for key in ['rule_name', 'alarm_id', 'room_id', 'trigger_condition', 'condition_value',
                    'action_type', 'action_target', 'enabled', 'priority']:
            if key in kwargs and kwargs[key] is not None:
                updates.append(f"{key} = ?")
                value = kwargs[key]
                if key == 'enabled' and DB_TYPE == 'sqlite':
                    value = 1 if value else 0
                values.append(value)

        if 'action_params' in kwargs:
            updates.append("action_params = ?")
            values.append(json.dumps(kwargs['action_params']) if kwargs['action_params'] else None)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(rule_id)

        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            sql = f"UPDATE smoke_alarm_response_rules SET {', '.join(updates)} WHERE rule_id = ?"
            cur.execute(sql, values)
            conn.commit()
            return cur.rowcount > 0
        else:
            # Convert to openGauss placeholders
            for i, _ in enumerate(updates[:-1]):  # Skip the last one which is updated_at
                updates[i] = updates[i].replace("?", f"${i+1}")
            updates[-1] = "updated_at = NOW()"
            values.insert(0, rule_id)  # rule_id goes first for WHERE clause
            sql = f"UPDATE smoke_alarm_response_rules SET {', '.join(updates)} WHERE rule_id = ${len(values)}"
            stmt = conn.prepare(sql)
            stmt(*values)
            return True
    finally:
        conn.close()


def delete_response_rule(rule_id):
    """删除自动化响应规则"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("DELETE FROM smoke_alarm_response_rules WHERE rule_id = ?", (rule_id,))
            conn.commit()
            return cur.rowcount > 0
        else:
            stmt = conn.prepare("DELETE FROM smoke_alarm_response_rules WHERE rule_id = $1")
            stmt(rule_id)
            return True
    finally:
        conn.close()


# ==================== 设备维护记录数据库操作 ====================

def get_maintenance_records(alarm_id, limit=50):
    """获取设备维护记录"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                SELECT id, alarm_id, maintenance_type, performed_by, maintenance_date,
                       next_maintenance_date, notes, cost, created_at
                FROM device_maintenance
                WHERE alarm_id = ?
                ORDER BY maintenance_date DESC
                LIMIT ?
            """, (alarm_id, limit))
            rows = cur.fetchall()
            return [{
                'id': r[0],
                'alarm_id': r[1],
                'maintenance_type': r[2],
                'performed_by': r[3],
                'maintenance_date': r[4],
                'next_maintenance_date': r[5],
                'notes': r[6],
                'cost': float(r[7]) if r[7] else None,
                'created_at': r[8]
            } for r in rows]
        else:
            stmt = conn.prepare("""
                SELECT id, alarm_id, maintenance_type, performed_by, maintenance_date,
                       next_maintenance_date, notes, cost, created_at
                FROM device_maintenance
                WHERE alarm_id = $1
                ORDER BY maintenance_date DESC
                LIMIT $2
            """)
            rows = stmt(alarm_id, limit)
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'alarm_id': r[1],
                    'maintenance_type': r[2],
                    'performed_by': r[3],
                    'maintenance_date': r[4].isoformat() if r[4] else None,
                    'next_maintenance_date': r[5].isoformat() if r[5] else None,
                    'notes': r[6],
                    'cost': float(r[7]) if r[7] else None,
                    'created_at': r[8].isoformat() if r[8] else None
                })
            return result
    finally:
        conn.close()


def add_maintenance_record(alarm_id, maintenance_type, performed_by, maintenance_date=None,
                           next_maintenance_date=None, notes=None, cost=None):
    """添加维护记录"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO device_maintenance
                (alarm_id, maintenance_type, performed_by, maintenance_date,
                 next_maintenance_date, notes, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (alarm_id, maintenance_type, performed_by, maintenance_date,
                  next_maintenance_date, notes, cost))
            conn.commit()

            # Update last_maintenance_date in smoke_alarm_state
            cur.execute("""
                UPDATE smoke_alarm_state
                SET last_maintenance_date = ?
                WHERE alarm_id = ?
            """, (maintenance_date or datetime.now(), alarm_id))
            conn.commit()
            return cur.lastrowid
        else:
            stmt = conn.prepare("""
                INSERT INTO device_maintenance
                (alarm_id, maintenance_type, performed_by, maintenance_date,
                 next_maintenance_date, notes, cost, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                RETURNING id
            """)
            rows = stmt(alarm_id, maintenance_type, performed_by, maintenance_date,
                       next_maintenance_date, notes, cost)
            record_id = None
            for row in rows:
                record_id = row[0]
                break

            # Update last_maintenance_date
            stmt2 = conn.prepare("""
                UPDATE smoke_alarm_state
                SET last_maintenance_date = $1
                WHERE alarm_id = $2
            """)
            stmt2(maintenance_date or datetime.now(), alarm_id)
            return record_id
    finally:
        conn.close()


def get_maintenance_due_devices(days_ahead=30):
    """获取需要维护的设备列表"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT s.alarm_id, s.room_id, s.location, s.device_model,
                       m.next_maintenance_date, m.maintenance_type
                FROM smoke_alarm_state s
                LEFT JOIN (
                    SELECT alarm_id, MAX(maintenance_date) as last_date
                    FROM device_maintenance
                    GROUP BY alarm_id
                ) last_m ON s.alarm_id = last_m.alarm_id
                LEFT JOIN device_maintenance m ON s.alarm_id = m.alarm_id
                    AND m.maintenance_date = last_m.last_date
                WHERE m.next_maintenance_date IS NOT NULL
                    AND DATE(m.next_maintenance_date) <= DATE('now', '+' || ? || ' days')
                ORDER BY m.next_maintenance_date
            """, (days_ahead,))
            rows = cur.fetchall()
            return [{
                'alarm_id': r[0],
                'room_id': r[1],
                'location': r[2],
                'device_model': r[3],
                'next_maintenance_date': r[4],
                'maintenance_type': r[5]
            } for r in rows]
        else:
            stmt = conn.prepare("""
                SELECT DISTINCT s.alarm_id, s.room_id, s.location, s.device_model,
                       m.next_maintenance_date, m.maintenance_type
                FROM smoke_alarm_state s
                LEFT JOIN LATERAL (
                    SELECT alarm_id, MAX(maintenance_date) as last_date
                    FROM device_maintenance
                    WHERE alarm_id = s.alarm_id
                    GROUP BY alarm_id
                ) last_m ON true
                LEFT JOIN device_maintenance m ON s.alarm_id = m.alarm_id
                    AND m.maintenance_date = last_m.last_date
                WHERE m.next_maintenance_date IS NOT NULL
                    AND m.next_maintenance_date <= CURRENT_DATE + $1 * INTERVAL '1 day'
                ORDER BY m.next_maintenance_date
            """)
            rows = stmt(days_ahead)
            result = []
            for r in rows:
                result.append({
                    'alarm_id': r[0],
                    'room_id': r[1],
                    'location': r[2],
                    'device_model': r[3],
                    'next_maintenance_date': r[4].isoformat() if r[4] else None,
                    'maintenance_type': r[5]
                })
            return result
    finally:
        conn.close()


def get_all_maintenance_records(limit=100, filter_alarm_id=None, filter_type=None):
    """获取所有设备的维护记录

    参数:
        limit: 返回记录数量限制
        filter_alarm_id: 筛选指定设备ID (可选)
        filter_type: 筛选维护类型 (可选)
    """
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()

            # 构建 SQL 查询
            sql = """
                SELECT id, alarm_id, maintenance_type, performed_by,
                       maintenance_date, next_maintenance_date, notes, cost
                FROM device_maintenance
                WHERE 1=1
            """
            params = []

            if filter_alarm_id:
                sql += " AND alarm_id = ?"
                params.append(filter_alarm_id)

            if filter_type:
                sql += " AND maintenance_type = ?"
                params.append(filter_type)

            sql += " ORDER BY maintenance_date DESC LIMIT ?"
            params.append(limit)

            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

            return [{
                'id': r[0],
                'alarm_id': r[1],
                'maintenance_type': r[2],
                'performed_by': r[3],
                'maintenance_date': r[4],
                'next_maintenance_date': r[5],
                'notes': r[6],
                'cost': float(r[7]) if r[7] else 0.0
            } for r in rows]
        else:
            # openGauss
            sql = """
                SELECT id, alarm_id, maintenance_type, performed_by,
                       maintenance_date, next_maintenance_date, notes, cost
                FROM device_maintenance
                WHERE 1=1
            """
            params = []
            param_count = 1

            if filter_alarm_id:
                sql += f" AND alarm_id = ${param_count}"
                params.append(filter_alarm_id)
                param_count += 1

            if filter_type:
                sql += f" AND maintenance_type = ${param_count}"
                params.append(filter_type)
                param_count += 1

            sql += f" ORDER BY maintenance_date DESC LIMIT ${param_count}"
            params.append(limit)

            stmt = conn.prepare(sql)
            rows = stmt(*params)

            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'alarm_id': r[1],
                    'maintenance_type': r[2],
                    'performed_by': r[3],
                    'maintenance_date': r[4].isoformat() if hasattr(r[4], 'isoformat') else str(r[4]),
                    'next_maintenance_date': r[5].isoformat() if r[5] and hasattr(r[5], 'isoformat') else (str(r[5]) if r[5] else None),
                    'notes': r[6],
                    'cost': float(r[7]) if r[7] else 0.0
                })
            return result
    finally:
        conn.close()


# ==================== 报警确认系统数据库操作 ====================

def acknowledge_alarm(alarm_id, event_id, acknowledged_by, response_time=None,
                     action_taken=None, resolution=None, notes=None):
    """确认报警"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO alarm_acknowledgments
                (alarm_id, event_id, acknowledged_by, response_time, action_taken, resolution, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (alarm_id, event_id, acknowledged_by, response_time, action_taken, resolution, notes))
            conn.commit()
            return cur.lastrowid
        else:
            stmt = conn.prepare("""
                INSERT INTO alarm_acknowledgments
                (alarm_id, event_id, acknowledged_by, acknowledged_at, response_time,
                 action_taken, resolution, notes)
                VALUES ($1, $2, $3, NOW(), $4, $5, $6, $7)
                RETURNING id
            """)
            rows = stmt(alarm_id, event_id, acknowledged_by, response_time, action_taken, resolution, notes)
            for row in rows:
                return row[0]
    finally:
        conn.close()


def get_alarm_acknowledgments(alarm_id, limit=50):
    """获取报警确认历史"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                SELECT id, alarm_id, event_id, acknowledged_by, acknowledged_at,
                       response_time, action_taken, resolution, notes
                FROM alarm_acknowledgments
                WHERE alarm_id = ?
                ORDER BY acknowledged_at DESC
                LIMIT ?
            """, (alarm_id, limit))
            rows = cur.fetchall()
            return [{
                'id': r[0],
                'alarm_id': r[1],
                'event_id': r[2],
                'acknowledged_by': r[3],
                'acknowledged_at': r[4],
                'response_time': r[5],
                'action_taken': r[6],
                'resolution': r[7],
                'notes': r[8]
            } for r in rows]
        else:
            stmt = conn.prepare("""
                SELECT id, alarm_id, event_id, acknowledged_by, acknowledged_at,
                       response_time, action_taken, resolution, notes
                FROM alarm_acknowledgments
                WHERE alarm_id = $1
                ORDER BY acknowledged_at DESC
                LIMIT $2
            """)
            rows = stmt(alarm_id, limit)
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'alarm_id': r[1],
                    'event_id': r[2],
                    'acknowledged_by': r[3],
                    'acknowledged_at': r[4].isoformat() if r[4] else None,
                    'response_time': r[5],
                    'action_taken': r[6],
                    'resolution': r[7],
                    'notes': r[8]
                })
            return result
    finally:
        conn.close()


# ==================== 统计分析数据库操作 ====================

def get_alarm_statistics(alarm_id=None, start_date=None, end_date=None):
    """获取报警统计数据"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            sql = """
                SELECT alarm_id, room_id, stat_date, total_alarms, false_alarms,
                       real_alarms, avg_response_time, max_smoke_level
                FROM alarm_statistics
                WHERE 1=1
            """
            params = []

            if alarm_id:
                sql += " AND alarm_id = ?"
                params.append(alarm_id)
            if start_date:
                sql += " AND stat_date >= ?"
                params.append(start_date)
            if end_date:
                sql += " AND stat_date <= ?"
                params.append(end_date)

            sql += " ORDER BY stat_date DESC"

            cur.execute(sql, params)
            rows = cur.fetchall()
            return [{
                'alarm_id': r[0],
                'room_id': r[1],
                'stat_date': r[2],
                'total_alarms': r[3],
                'false_alarms': r[4],
                'real_alarms': r[5],
                'avg_response_time': r[6],
                'max_smoke_level': r[7]
            } for r in rows]
        else:
            sql = """
                SELECT alarm_id, room_id, stat_date, total_alarms, false_alarms,
                       real_alarms, avg_response_time, max_smoke_level
                FROM alarm_statistics
                WHERE 1=1
            """
            param_count = 1
            params = []

            if alarm_id:
                sql += f" AND alarm_id = ${param_count}"
                params.append(alarm_id)
                param_count += 1
            if start_date:
                sql += f" AND stat_date >= ${param_count}"
                params.append(start_date)
                param_count += 1
            if end_date:
                sql += f" AND stat_date <= ${param_count}"
                params.append(end_date)
                param_count += 1

            sql += " ORDER BY stat_date DESC"

            stmt = conn.prepare(sql)
            rows = stmt(*params) if params else stmt()
            result = []
            for r in rows:
                result.append({
                    'alarm_id': r[0],
                    'room_id': r[1],
                    'stat_date': r[2].isoformat() if r[2] else None,
                    'total_alarms': r[3],
                    'false_alarms': r[4],
                    'real_alarms': r[5],
                    'avg_response_time': r[6],
                    'max_smoke_level': r[7]
                })
            return result
    finally:
        conn.close()


def update_daily_statistics(alarm_id, stat_date=None):
    """更新每日统计数据（基于当天的事件和确认记录）"""
    if stat_date is None:
        stat_date = date.today()

    conn = get_connection()
    try:
        # Get room_id for this alarm
        room_id = None
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("SELECT room_id FROM smoke_alarm_state WHERE alarm_id = ?", (alarm_id,))
            row = cur.fetchone()
            if row:
                room_id = row[0]
        else:
            stmt = conn.prepare("SELECT room_id FROM smoke_alarm_state WHERE alarm_id = $1")
            rows = stmt(alarm_id)
            for row in rows:
                room_id = row[0]
                break

        # Count events and calculate statistics
        if DB_TYPE == 'sqlite':
            cur.execute("""
                SELECT COUNT(*) as total,
                       MAX(smoke_level) as max_level
                FROM smoke_alarm_events
                WHERE alarm_id = ?
                    AND event_type IN ('ALARM_TRIGGERED', 'ALARM_CLEARED')
                    AND DATE(timestamp) = DATE(?)
            """, (alarm_id, stat_date))
            event_stats = cur.fetchone()

            cur.execute("""
                SELECT COUNT(*) as false_count,
                       AVG(response_time) as avg_time
                FROM alarm_acknowledgments
                WHERE alarm_id = ?
                    AND DATE(acknowledged_at) = DATE(?)
            """, (alarm_id, stat_date))
            ack_stats = cur.fetchone()

            false_alarms = 0
            if ack_stats:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM alarm_acknowledgments
                    WHERE alarm_id = ?
                        AND DATE(acknowledged_at) = DATE(?)
                        AND resolution = 'false_alarm'
                """, (alarm_id, stat_date))
                false_alarms = cur.fetchone()[0]

            total_alarms = event_stats[0] if event_stats else 0
            max_smoke = event_stats[1] if event_stats else 0.0
            avg_response = ack_stats[1] if ack_stats else None
            real_alarms = total_alarms - false_alarms

            # Upsert statistics
            cur.execute("""
                INSERT OR REPLACE INTO alarm_statistics
                (alarm_id, room_id, stat_date, total_alarms, false_alarms, real_alarms,
                 avg_response_time, max_smoke_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (alarm_id, room_id, stat_date, total_alarms, false_alarms, real_alarms,
                  avg_response, max_smoke))
            conn.commit()
        else:
            # openGauss implementation (similar logic but with $placeholders)
            stmt = conn.prepare("""
                SELECT COUNT(*) as total,
                       MAX(smoke_level) as max_level
                FROM smoke_alarm_events
                WHERE alarm_id = $1
                    AND event_type IN ('ALARM_TRIGGERED', 'ALARM_CLEARED')
                    AND DATE(timestamp) = $2
            """)
            rows = stmt(alarm_id, stat_date)
            event_stats = None
            for row in rows:
                event_stats = row
                break

            stmt = conn.prepare("""
                SELECT COUNT(*) as false_count,
                       AVG(response_time) as avg_time
                FROM alarm_acknowledgments
                WHERE alarm_id = $1
                    AND DATE(acknowledged_at) = $2
                    AND resolution = 'false_alarm'
            """)
            rows = stmt(alarm_id, stat_date)
            false_alarms = 0
            avg_response = None
            for row in rows:
                false_alarms = row[0]
                avg_response = row[1]
                break

            total_alarms = event_stats[0] if event_stats else 0
            max_smoke = event_stats[1] if event_stats else 0.0
            real_alarms = total_alarms - false_alarms

            # Check if record exists
            stmt = conn.prepare("""
                SELECT id FROM alarm_statistics
                WHERE alarm_id = $1 AND stat_date = $2
            """)
            rows = stmt(alarm_id, stat_date)
            exists = False
            for _ in rows:
                exists = True
                break

            if exists:
                stmt = conn.prepare("""
                    UPDATE alarm_statistics
                    SET total_alarms = $1, false_alarms = $2, real_alarms = $3,
                        avg_response_time = $4, max_smoke_level = $5
                    WHERE alarm_id = $6 AND stat_date = $7
                """)
                stmt(total_alarms, false_alarms, real_alarms, avg_response, max_smoke,
                    alarm_id, stat_date)
            else:
                stmt = conn.prepare("""
                    INSERT INTO alarm_statistics
                    (alarm_id, room_id, stat_date, total_alarms, false_alarms, real_alarms,
                     avg_response_time, max_smoke_level, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """)
                stmt(alarm_id, room_id, stat_date, total_alarms, false_alarms, real_alarms,
                    avg_response, max_smoke)

        return True
    finally:
        conn.close()


# ==================== 房间管理增强操作 ====================

def create_room(room_id, room_name, floor=1, area=None, description=None):
    """创建新房间"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO rooms (room_id, room_name, floor, area, description)
                VALUES (?, ?, ?, ?, ?)
            """, (room_id, room_name, floor, area, description))
            conn.commit()
            return True
        else:
            stmt = conn.prepare("""
                INSERT INTO rooms (room_id, room_name, floor, area, description, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
            """)
            stmt(room_id, room_name, floor, area, description)
            return True
    finally:
        conn.close()


def update_room(room_id, **kwargs):
    """更新房间信息"""
    conn = get_connection()
    try:
        updates = []
        values = []

        for key in ['room_name', 'floor', 'area', 'description']:
            if key in kwargs and kwargs[key] is not None:
                updates.append(f"{key} = ?")
                values.append(kwargs[key])

        if not updates:
            return False

        values.append(room_id)

        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            sql = f"UPDATE rooms SET {', '.join(updates)} WHERE room_id = ?"
            cur.execute(sql, values)
            conn.commit()
            return cur.rowcount > 0
        else:
            # Convert to openGauss placeholders
            for i, _ in enumerate(updates):
                updates[i] = updates[i].replace("?", f"${i+1}")
            sql = f"UPDATE rooms SET {', '.join(updates)} WHERE room_id = ${len(values)}"
            stmt = conn.prepare(sql)
            stmt(*values)
            return True
    finally:
        conn.close()


def delete_room(room_id):
    """删除房间"""
    conn = get_connection()
    try:
        if DB_TYPE == 'sqlite':
            cur = conn.cursor()
            cur.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
            conn.commit()
            return cur.rowcount > 0
        else:
            stmt = conn.prepare("DELETE FROM rooms WHERE room_id = $1")
            stmt(room_id)
            return True
    finally:
        conn.close()

