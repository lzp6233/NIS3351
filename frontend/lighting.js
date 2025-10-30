/**
 * 全屋灯具控制 JavaScript
 * 功能：灯具控制、智能调节、批量操作
 */

// API 基础URL
const API_BASE = 'http://localhost:5000';

// 灯具数据
let lights = [];
let selectedLights = new Set();
let currentLightId = '';
let autoRefreshTimer = null;
let isAutoRefreshing = false;


// DOM 元素
let lightingGrid, statusSpan, refreshBtn, batchControlBtn, lightSelect;
let allOnBtn, allOffBtn, autoModeBtn, manualModeBtn;
let batchModal, batchPower, batchBrightness, batchColorTemp, batchAutoMode;



// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initElements();
    initEventListeners();
    loadLights();
    startAutoRefreshTimer();
});

function initElements() {
    lightingGrid = document.getElementById('lightingGrid');
    statusSpan = document.getElementById('status');
    refreshBtn = document.getElementById('refreshBtn');
    batchControlBtn = document.getElementById('batchControlBtn');
    lightSelect = document.getElementById('lightSelect');
    
    allOnBtn = document.getElementById('allOnBtn');
    allOffBtn = document.getElementById('allOffBtn');
    autoModeBtn = document.getElementById('autoModeBtn');
    manualModeBtn = document.getElementById('manualModeBtn');
    
    batchModal = document.getElementById('batchModal');
    batchPower = document.getElementById('batchPower');
    batchBrightness = document.getElementById('batchBrightness');
    batchColorTemp = document.getElementById('batchColorTemp');
    batchAutoMode = document.getElementById('batchAutoMode');
}

function initEventListeners() {
    // 刷新按钮
    refreshBtn.addEventListener('click', async () => {
        if (currentLightId) {
            // 模拟房间亮度变化并触发智能调节
            await simulateRoomBrightnessAndAutoAdjust(currentLightId);
            // 重新加载灯具状态
            await loadLights();
        } else {
            loadLights();
        }
    });
    
    // 灯具选择
    lightSelect.addEventListener('change', (e) => {
        currentLightId = e.target.value;
        if (currentLightId) {
            updateStats(currentLightId);
        }
    });
    
    // 全局控制按钮
    allOnBtn.addEventListener('click', () => batchControlAll(true));
    allOffBtn.addEventListener('click', () => batchControlAll(false));
    autoModeBtn.addEventListener('click', () => setAllAutoMode(true));
    manualModeBtn.addEventListener('click', () => setAllAutoMode(false));
    
    // 批量控制按钮
    batchControlBtn.addEventListener('click', openBatchModal);
    
    // 批量控制模态框
    const closeBtn = document.querySelector('.close');
    const cancelBtn = document.getElementById('cancelBatchBtn');
    const applyBtn = document.getElementById('applyBatchBtn');
    
    closeBtn.addEventListener('click', closeBatchModal);
    cancelBtn.addEventListener('click', closeBatchModal);
    applyBtn.addEventListener('click', applyBatchControl);
    
    // 批量控制滑块
    batchBrightness.addEventListener('input', function() {
        document.getElementById('batchBrightnessValue').textContent = this.value + '%';
    });
    
    batchColorTemp.addEventListener('input', function() {
        document.getElementById('batchColorTempValue').textContent = this.value + 'K';
    });
    
    // 点击模态框外部关闭
    window.addEventListener('click', function(event) {
        if (event.target === batchModal) {
            closeBatchModal();
        }
    });
}

// 加载灯具数据
async function loadLights() {
    try {
        statusSpan.textContent = '正在加载...';
        const response = await fetch(`${API_BASE}/lighting`);
        if (!response.ok) throw new Error('加载失败');
        
        lights = await response.json();
        // 规范化字段类型，确保 room_brightness 为数字以便渲染到两处
        lights = lights.map(l => {
            const rb = (typeof l.room_brightness === 'string') ? parseFloat(l.room_brightness) : l.room_brightness;
            return {
                ...l,
                room_brightness: Number.isFinite(rb) ? rb : l.room_brightness
            };
        });
        renderLights();
        updateLightSelect();
        statusSpan.textContent = `已加载 ${lights.length} 个灯具`;
    } catch (error) {
        console.error('加载灯具失败:', error);
        statusSpan.textContent = '加载失败';
    }
}

// 更新灯具选择下拉框
function updateLightSelect() {
    lightSelect.innerHTML = '';
    lights.forEach(light => {
        const option = document.createElement('option');
        option.value = light.light_id;
        const deviceLabel = getDeviceNameByLightId(light.light_id);
        option.textContent = `${getLightDisplayName(light.light_id)} (${deviceLabel})`;
        lightSelect.appendChild(option);
    });

    // 默认选择 light_room1（如存在），否则选第一项
    const defaultId = 'light_room1';
    if (!currentLightId) {
        const hasDefault = Array.from(lightSelect.options).some(opt => opt.value === defaultId);
        currentLightId = hasDefault ? defaultId : (lightSelect.options[0] ? lightSelect.options[0].value : '');
    }
    lightSelect.value = currentLightId;
    if (currentLightId) updateStats(currentLightId);
}

// 更新统计信息
function updateStats(lightId) {
    const light = lights.find(l => l.light_id === lightId);
    if (light) {
        document.getElementById('currentBrightness').textContent = `${light.brightness}%`;
        const rb = typeof light.room_brightness === 'number' ? light.room_brightness.toFixed(1) : '--';
        document.getElementById('currentRoomBrightness').textContent = `${rb} lux`;
        document.getElementById('autoModeStatus').textContent = light.auto_mode ? '开启' : '关闭';
        document.getElementById('colorTemp').textContent = `${light.color_temp}K`;
    }
}

// 渲染灯具列表
function renderLights() {
    lightingGrid.innerHTML = '';
    
    lights.forEach(light => {
        const lightCard = createLightCard(light);
        lightingGrid.appendChild(lightCard);
    });
}

// 创建灯具卡片
function createLightCard(light) {
    const card = document.createElement('div');
    card.className = 'light-card';
    card.innerHTML = `
        <div class="light-header">
            <h4>${getLightDisplayName(light.light_id)}</h4>
            <div class="light-status ${light.power ? 'on' : 'off'}">
                ${light.power ? '💡 开启' : '🔘 关闭'}
            </div>
        </div>
        
        <div class="light-controls">
            <!-- 开关 + 智能模式（同一行） -->
            <div class="control-row">
                <div class="control-group">
                    <button class="light-btn ${light.power ? 'active' : ''}" 
                            onclick="toggleLight('${light.light_id}', ${!light.power})">
                        ${light.power ? '关闭' : '开启'}
                    </button>
                </div>
                <!-- 智能模式 -->
                <div class="control-group auto-mode-group">
                    <span class="switch-text">智能调节</span>
                    <label class="switch">
                        <input type="checkbox" ${light.auto_mode ? 'checked' : ''} 
                               onchange="setAutoMode('${light.light_id}', this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
            
            <!-- 亮度控制 -->
            <div class="control-group">
                <label>亮度: ${light.brightness}%</label>
                <input type="range" min="0" max="100" value="${light.brightness}" 
                       onchange="setBrightness('${light.light_id}', this.value)">
            </div>
            
            <!-- 色温控制 -->
            <div class="control-group">
                <label>色温: ${light.color_temp}K</label>
                <input type="range" min="2700" max="6500" value="${light.color_temp}" 
                       onchange="setColorTemp('${light.light_id}', this.value)">
            </div>
            
            
            
            <!-- 房间亮度显示 -->
            <div class="room-brightness">
                <small>房间亮度: ${typeof light.room_brightness === 'number' ? light.room_brightness.toFixed(1) : '--'} lux</small>
            </div>
        </div>
    `;
    
    return card;
}

// 获取灯具显示名称
function getLightDisplayName(lightId) {
    const nameMap = {
        'light_room1': '卧室1',
        'light_room2': '卧室2', 
        'light_living': '客厅',
        'light_kitchen': '厨房'
    };
    return nameMap[lightId] || lightId;
}

// 根据 light_id 映射设备标识（用于下拉框括号内显示）
function getDeviceNameByLightId(lightId) {
    const deviceMap = {
        'light_room1': 'room1',
        'light_room2': 'room2',
        'light_living': 'living',
        'light_kitchen': 'kitchen'
    };
    return deviceMap[lightId] || lightId;
}

// 根据 light_id 获取目标照度（lux）
function getTargetLuxForLightId(lightId) {
    const targetMap = {
        'light_room1': 300,
        'light_room2': 300,
        'light_living': 600,
        'light_kitchen': 500
    };
    return targetMap[lightId] || 400;
}

// 启动自动刷新定时器：每10秒按需自动调节并刷新
function startAutoRefreshTimer() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
    autoRefreshTimer = setInterval(async () => {
        if (isAutoRefreshing) return;
        isAutoRefreshing = true;
        try {
            const lid = currentLightId || 'light_room1';
            await simulateRoomBrightnessAndAutoAdjust(lid);
            await loadLights();
        } catch (e) {
            console.error('自动刷新失败:', e);
        } finally {
            isAutoRefreshing = false;
        }
    }, 10000);
}

// 控制灯具开关
async function toggleLight(lightId, power) {
    try {
        const response = await fetch(`${API_BASE}/lighting/${lightId}/control`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ power })
        });
        
        if (response.ok) {
            loadLights(); // 重新加载数据
        } else {
            alert('控制失败');
        }
    } catch (error) {
        console.error('控制灯具失败:', error);
        alert('控制失败');
    }
}

// 设置亮度
async function setBrightness(lightId, brightness) {
    try {
        const response = await fetch(`${API_BASE}/lighting/${lightId}/control`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ brightness: parseInt(brightness) })
        });
        
        if (response.ok) {
            loadLights();
        }
    } catch (error) {
        console.error('设置亮度失败:', error);
    }
}

// 设置色温
async function setColorTemp(lightId, colorTemp) {
    try {
        const response = await fetch(`${API_BASE}/lighting/${lightId}/control`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ color_temp: parseInt(colorTemp) })
        });
        
        if (response.ok) {
            loadLights();
        }
    } catch (error) {
        console.error('设置色温失败:', error);
    }
}

// 设置智能模式
async function setAutoMode(lightId, autoMode) {
    try {
        const response = await fetch(`${API_BASE}/lighting/${lightId}/control`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ auto_mode: autoMode })
        });
        
        if (response.ok) {
            // 开启智能模式后，立即触发一次智能调节并刷新
            if (autoMode) {
                await simulateRoomBrightnessAndAutoAdjust(lightId);
            }
            await loadLights();
        }
    } catch (error) {
        console.error('设置智能模式失败:', error);
    }
}

// 智能调节灯具
async function autoAdjustLight(lightId) {
    try {
        const light = lights.find(l => l.light_id === lightId);
        if (!light) return;
        
        const response = await fetch(`${API_BASE}/lighting/${lightId}/auto-adjust`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ room_brightness: light.room_brightness || 50 })
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(`智能调节完成！\n房间亮度: ${result.room_brightness} lux\n亮度调整: ${result.old_brightness}% → ${result.new_brightness}%`);
            loadLights();
        }
    } catch (error) {
        console.error('智能调节失败:', error);
        alert('智能调节失败');
    }
}

// 批量控制所有灯具
async function batchControlAll(power) {
    try {
        const lightConfigs = lights.map(light => ({
            light_id: light.light_id,
            power: power
        }));
        
        const response = await fetch(`${API_BASE}/lighting/batch-control`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ lights: lightConfigs })
        });
        
        if (response.ok) {
            loadLights();
        }
    } catch (error) {
        console.error('批量控制失败:', error);
        alert('批量控制失败');
    }
}

// 设置所有灯具的智能模式
async function setAllAutoMode(autoMode) {
    try {
        const lightConfigs = lights.map(light => ({
            light_id: light.light_id,
            auto_mode: autoMode
        }));
        
        const response = await fetch(`${API_BASE}/lighting/batch-control`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ lights: lightConfigs })
        });
        
        if (response.ok) {
            loadLights();
        }
    } catch (error) {
        console.error('设置智能模式失败:', error);
        alert('设置智能模式失败');
    }
}

// 打开批量控制模态框
function openBatchModal() {
    batchModal.style.display = 'block';
    
    // 重置表单
    batchPower.value = '';
    batchBrightness.value = '50';
    batchColorTemp.value = '4000';
    batchAutoMode.value = '';
    
    document.getElementById('batchBrightnessValue').textContent = '50%';
    document.getElementById('batchColorTempValue').textContent = '4000K';
}

// 关闭批量控制模态框
function closeBatchModal() {
    batchModal.style.display = 'none';
}

// 应用批量控制
async function applyBatchControl() {
    try {
        const lightConfigs = lights.map(light => {
            const config = { light_id: light.light_id };
            
            if (batchPower.value !== '') {
                config.power = batchPower.value === 'true';
            }
            if (batchBrightness.value !== '') {
                config.brightness = parseInt(batchBrightness.value);
            }
            if (batchColorTemp.value !== '') {
                config.color_temp = parseInt(batchColorTemp.value);
            }
            if (batchAutoMode.value !== '') {
                config.auto_mode = batchAutoMode.value === 'true';
            }
            
            return config;
        });
        
        const response = await fetch(`${API_BASE}/lighting/batch-control`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ lights: lightConfigs })
        });
        
        if (response.ok) {
            closeBatchModal();
            loadLights();
        } else {
            alert('批量控制失败');
        }
    } catch (error) {
        console.error('批量控制失败:', error);
        alert('批量控制失败');
    }
}


// 统一的房间亮度模拟和智能调节函数
async function simulateRoomBrightnessAndAutoAdjust(lightId) {
    try {
        // 基于房间类型与时段生成更贴近实际的房间亮度
        const target = getTargetLuxForLightId(lightId);
        const hour = new Date().getHours();
        // 白天略高、夜晚略低的时段因子（0.6 ~ 1.1）
        const dayFactor = (hour >= 7 && hour <= 18) ? 1.0 + (Math.random() * 0.1) : 0.6 + (Math.random() * 0.2);
        const base = target * dayFactor;
        // 近似正态噪声：多次均匀随机求平均
        const noise = target * 0.15 * (((Math.random()+Math.random()+Math.random())/3) - 0.5) * 2; // ≈ ±15%
        let roomBrightness = Math.max(0, base + noise);
        roomBrightness = Math.round(roomBrightness * 10) / 10; // 一位小数
        
        // 调用智能调节API
        const response = await fetch(`${API_BASE}/lighting/${lightId}/auto-adjust`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                room_brightness: roomBrightness
            })
        });
        
        if (response.ok) {
            // 乐观更新本地内存中的房间亮度，保证 UI 立即同步
            lights = lights.map(l => l.light_id === lightId ? { ...l, room_brightness: roomBrightness } : l);
            if (currentLightId === lightId) {
                updateStats(lightId);
            }
            statusSpan.textContent = `房间亮度: ${roomBrightness} lux`;
        } else {
            console.error('智能调节失败:', response.status);
            statusSpan.textContent = '智能调节失败';
        }
    } catch (error) {
        console.error('模拟房间亮度和智能调节失败:', error);
        statusSpan.textContent = '刷新失败';
    }
}