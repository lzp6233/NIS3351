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


// DOM 元素
let lightingGrid, statusSpan, refreshBtn, batchControlBtn, lightSelect;
let allOnBtn, allOffBtn, autoModeBtn, manualModeBtn;
let batchModal, batchPower, batchBrightness, batchColorTemp, batchAutoMode;



// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initElements();
    initEventListeners();
    loadLights();
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
    lightSelect.innerHTML = '<option value="">请选择灯具</option>';
    lights.forEach(light => {
        const option = document.createElement('option');
        option.value = light.light_id;
        option.textContent = `${light.light_id} (${light.device_id})`;
        lightSelect.appendChild(option);
    });
}

// 更新统计信息
function updateStats(lightId) {
    const light = lights.find(l => l.light_id === lightId);
    if (light) {
        document.getElementById('currentBrightness').textContent = `${light.brightness}%`;
        document.getElementById('currentRoomBrightness').textContent = `${light.room_brightness || 0} lux`;
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
            <!-- 开关控制 -->
            <div class="control-group">
                <button class="light-btn ${light.power ? 'active' : ''}" 
                        onclick="toggleLight('${light.light_id}', ${!light.power})">
                    ${light.power ? '关闭' : '开启'}
                </button>
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
            
            <!-- 智能模式 -->
            <div class="control-group">
                <label class="switch">
                    <input type="checkbox" ${light.auto_mode ? 'checked' : ''} 
                           onchange="setAutoMode('${light.light_id}', this.checked)">
                    <span class="slider"></span>
                    智能调节
                </label>
            </div>
            
            <!-- 房间亮度显示 -->
            <div class="room-brightness">
                <small>房间亮度: ${light.room_brightness ? light.room_brightness.toFixed(1) : '--'} lux</small>
            </div>
            
            <!-- 智能调节按钮 -->
            <div class="control-group">
                <button class="auto-btn" onclick="autoAdjustLight('${light.light_id}')">
                    🔄 智能调节
                </button>
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
            loadLights();
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
        // 生成模拟房间亮度
        const now = new Date();
        const hour = now.getHours();
        
        // 模拟房间亮度：白天高，夜晚低
        let roomBrightness;
        if (6 <= hour && hour <= 18) {  // 白天
            roomBrightness = Math.random() * 40 + 60;  // 60-100 lux
        } else {  // 夜晚
            roomBrightness = Math.random() * 30 + 10;  // 10-40 lux
        }
        
        roomBrightness = Math.round(roomBrightness * 10) / 10;  // 保留一位小数
        
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
            const result = await response.json();
            console.log('智能调节结果:', result.message);
            statusSpan.textContent = `房间亮度: ${roomBrightness} lux - ${result.message}`;
        } else {
            console.error('智能调节失败:', response.status);
            statusSpan.textContent = '智能调节失败';
        }
    } catch (error) {
        console.error('模拟房间亮度和智能调节失败:', error);
        statusSpan.textContent = '刷新失败';
    }
}

