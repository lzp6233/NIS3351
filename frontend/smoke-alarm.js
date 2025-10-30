// API 基础地址
const API_BASE = 'http://localhost:5000';
let selectedAlarmId = null;

// 房间固定排序
const ROOM_ORDER = ['living_room', 'bedroom1', 'bedroom2', 'kitchen', 'study'];

// 排序函数
function sortByRoomOrder(items, idField = 'location') {
    return items.sort((a, b) => {
        const indexA = ROOM_ORDER.indexOf(a[idField]);
        const indexB = ROOM_ORDER.indexOf(b[idField]);
        // 如果房间不在列表中，放到最后
        if (indexA === -1 && indexB === -1) return 0;
        if (indexA === -1) return 1;
        if (indexB === -1) return -1;
        return indexA - indexB;
    });
}

// 加载所有烟雾报警器
async function loadAlarms() {
    try {
        const response = await fetch(`${API_BASE}/smoke_alarms`);
        const alarms = await response.json();

        // 按固定顺序排序
        const sortedAlarms = sortByRoomOrder(alarms, 'location');

        document.getElementById('loading').style.display = 'none';
        document.getElementById('alarms-grid').style.display = 'grid';

        const grid = document.getElementById('alarms-grid');
        grid.innerHTML = '';

        sortedAlarms.forEach(alarm => {
            const card = createAlarmCard(alarm);
            grid.appendChild(card);
        });

        if (sortedAlarms.length > 0 && !selectedAlarmId) {
            selectedAlarmId = sortedAlarms[0].alarm_id;
            loadEvents(selectedAlarmId);
        }
    } catch (error) {
        console.error('加载报警器失败:', error);
        document.getElementById('loading').textContent = '加载失败，请检查后端服务';
    }
}

// 创建报警器卡片
function createAlarmCard(alarm) {
    const card = document.createElement('div');
    card.className = 'alarm-card';
    if (alarm.alarm_active) {
        card.classList.add('alarm-active');
    }

    const locationNames = {
        'living_room': '客厅',
        'bedroom': '卧室',
        'bedroom1': '主卧',
        'bedroom2': '次卧',
        'kitchen': '厨房',
        'study': '书房'
    };

    const statusClass = alarm.alarm_active ? 'status-danger' :
                       alarm.smoke_level > 15 ? 'status-warning' : 'status-normal';
    const statusText = alarm.alarm_active ? '🚨 报警中' :
                      alarm.smoke_level > 15 ? '⚠️ 警告' : '✓ 正常';

    const batteryClass = alarm.battery < 20 ? 'low' : alarm.battery < 50 ? 'medium' : '';

    card.innerHTML = `
        <div class="alarm-header">
            <div class="alarm-location">${locationNames[alarm.location] || alarm.location}</div>
            <div class="alarm-status ${statusClass}">${statusText}</div>
        </div>

        <div class="alarm-details">
            <div class="detail-row">
                <span class="detail-label">烟雾浓度</span>
                <span class="detail-value">${alarm.smoke_level.toFixed(1)}%</span>
            </div>
            <div class="smoke-level-bar">
                <div class="smoke-level-fill" style="width: ${Math.min(alarm.smoke_level, 100)}%">
                    ${alarm.smoke_level.toFixed(1)}%
                </div>
            </div>

            <div class="detail-row">
                <span class="detail-label">电池电量</span>
                <span class="detail-value">
                    ${alarm.battery}%
                    <span class="battery-indicator">
                        <div class="battery-fill ${batteryClass}" style="width: ${alarm.battery}%"></div>
                    </span>
                </span>
            </div>

            <div class="detail-row">
                <span class="detail-label">灵敏度</span>
                <span class="detail-value">${alarm.sensitivity}</span>
            </div>

            <div class="detail-row">
                <span class="detail-label">测试模式</span>
                <span class="detail-value">${alarm.test_mode ? '开启' : '关闭'}</span>
            </div>
        </div>

        <div class="controls">
            <button class="btn btn-test" onclick="toggleTest('${alarm.alarm_id}', ${!alarm.test_mode})">
                ${alarm.test_mode ? '停止测试' : '开始测试'}
            </button>
            ${alarm.alarm_active ? `
                <button class="btn btn-acknowledge" onclick="acknowledgeAlarm('${alarm.alarm_id}')">
                    确认报警
                </button>
            ` : ''}
            <button class="btn btn-sensitivity" onclick="showEvents('${alarm.alarm_id}')">
                查看事件
            </button>
        </div>
    `;

    return card;
}

// 切换测试模式
async function toggleTest(alarmId, enable) {
    try {
        const response = await fetch(`${API_BASE}/smoke_alarms/${alarmId}/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_mode: enable })
        });

        if (response.ok) {
            loadAlarms();
        }
    } catch (error) {
        console.error('切换测试模式失败:', error);
    }
}

// 确认报警
async function acknowledgeAlarm(alarmId) {
    try {
        const response = await fetch(`${API_BASE}/smoke_alarms/${alarmId}/acknowledge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            loadAlarms();
        }
    } catch (error) {
        console.error('确认报警失败:', error);
    }
}

// 显示事件
function showEvents(alarmId) {
    selectedAlarmId = alarmId;
    loadEvents(alarmId);
    document.getElementById('events-section').style.display = 'block';
    document.getElementById('events-section').scrollIntoView({ behavior: 'smooth' });
}

// 加载事件列表
async function loadEvents(alarmId) {
    try {
        const response = await fetch(`${API_BASE}/smoke_alarms/${alarmId}/events?limit=20`);
        const events = await response.json();

        const list = document.getElementById('events-list');
        list.innerHTML = '';

        if (events.length === 0) {
            list.innerHTML = '<p style="color: #999;">暂无事件记录</p>';
            return;
        }

        events.forEach(event => {
            const item = document.createElement('div');
            item.className = `event-item ${event.event_type}`;

            const eventTypeNames = {
                'ALARM_TRIGGERED': '🚨 报警触发',
                'ALARM_CLEARED': '✅ 报警解除',
                'LOW_BATTERY': '🔋 低电量警告',
                'TEST_STARTED': '🔧 测试开始',
                'TEST_STOPPED': '🔧 测试停止',
                'INIT': '📡 初始化'
            };

            item.innerHTML = `
                <div class="event-type">${eventTypeNames[event.event_type] || event.event_type}</div>
                <div class="event-detail">${event.detail || ''}</div>
                ${event.smoke_level ? `<div class="event-detail">烟雾浓度: ${event.smoke_level.toFixed(1)}%</div>` : ''}
                <div class="event-time">${new Date(event.timestamp).toLocaleString('zh-CN')}</div>
            `;

            list.appendChild(item);
        });
    } catch (error) {
        console.error('加载事件失败:', error);
    }
}

// 自动刷新数据
setInterval(loadAlarms, 3000);

// 页面加载时初始化
loadAlarms();
