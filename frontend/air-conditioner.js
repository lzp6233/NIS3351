// API 基础地址
const API_BASE = 'http://localhost:5000';

// 初始化图表
const chart = echarts.init(document.getElementById('chart'));
let currentDevice = 'all';

// 图表配置
const option = {
    title: { 
        text: '温湿度实时监控',
        left: 'center'
    },
    tooltip: {
        trigger: 'axis',
        axisPointer: {
            type: 'cross'
        }
    },
    legend: {
        data: ['温度', '湿度'],
        top: 30
    },
    grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
    },
    xAxis: {
        type: 'category',
        boundaryGap: false,
        data: []
    },
    yAxis: [
        {
            type: 'value',
            name: '温度 (°C)',
            position: 'left',
            axisLabel: {
                formatter: '{value} °C'
            }
        },
        {
            type: 'value',
            name: '湿度 (%)',
            position: 'right',
            axisLabel: {
                formatter: '{value} %'
            }
        }
    ],
    series: [
        {
            name: '温度',
            type: 'line',
            smooth: true,
            yAxisIndex: 0,
            data: [],
            itemStyle: {
                color: '#FF6B6B'
            }
        },
        {
            name: '湿度',
            type: 'line',
            smooth: true,
            yAxisIndex: 1,
            data: [],
            itemStyle: {
                color: '#4ECDC4'
            }
        }
    ]
};

chart.setOption(option);

// 加载设备列表
async function loadDevices() {
    try {
        console.log('正在请求设备列表:', `${API_BASE}/devices`);
        console.log('当前页面 Origin:', window.location.origin);
        
        // 添加详细的请求配置和调试信息
        const requestOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors', // 明确指定 CORS 模式
            credentials: 'omit' // 不发送凭据
        };
        
        console.log('请求配置:', requestOptions);
        // 添加时间戳避免缓存
        const url = `${API_BASE}/devices?_t=${Date.now()}`;
        const response = await fetch(url, requestOptions);
        console.log('响应状态:', response.status, response.statusText);
        console.log('响应头:', [...response.headers.entries()]);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const devices = await response.json();
        console.log('获取到设备数据:', devices);
        
        const select = document.getElementById('deviceSelect');
        select.innerHTML = '';  // 清空选项
        
        devices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.device_id;
            option.textContent = `${device.device_id} (${device.data_count} 条数据)`;
            select.appendChild(option);
        });
        
        // 默认选择第一个设备
        if (devices.length > 0) {
            currentDevice = devices[0].device_id;
        }
        
        updateStatus('设备列表加载成功', 'success');
    } catch (error) {
        console.error('加载设备列表失败:', error);
        console.error('错误详情:', error.message);
        updateStatus(`加载设备失败: ${error.message}`, 'error');
    }
}

// 加载历史数据
async function loadHistory(deviceId) {
    try {
        updateStatus('加载中...', 'loading');
        
        // 如果没有指定设备，使用当前设备
        if (!deviceId) {
            deviceId = currentDevice || 'room1';
        }
        
        const baseUrl = `${API_BASE}/history/${deviceId}?limit=50`;
        
        // 添加时间戳避免缓存
        const url = baseUrl + `&_t=${Date.now()}`;
        
        console.log('正在请求历史数据:', url);
        
        const requestOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors',
            credentials: 'omit'
        };
        
        const response = await fetch(url, requestOptions);
        console.log('历史数据响应状态:', response.status, response.statusText);
        console.log('历史数据响应头:', [...response.headers.entries()]);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('获取到历史数据:', data.length, '条记录');
        
        if (data.length === 0) {
            updateStatus('暂无数据', 'warning');
            return;
        }
        
        // 按时间排序（升序）
        data.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // 提取数据
        const times = data.map(d => new Date(d.timestamp).toLocaleTimeString());
        const temperatures = data.map(d => d.temperature);
        const humidities = data.map(d => d.humidity);
        
        // 更新图表
        option.xAxis.data = times;
        option.series[0].data = temperatures;
        option.series[1].data = humidities;
        chart.setOption(option);
        
        // 更新统计信息
        const latest = data[data.length - 1];
        document.getElementById('currentTemp').textContent = `${latest.temperature}°C`;
        document.getElementById('currentHum').textContent = `${latest.humidity}%`;
        document.getElementById('dataCount').textContent = data.length;
        
        // 计算舒适指数
        updateComfortIndex(latest.temperature, latest.humidity);
        
        updateStatus('数据加载成功', 'success');
        
    } catch (error) {
        console.error('加载数据失败:', error);
        console.error('错误详情:', error.message);
        updateStatus(`加载数据失败: ${error.message}`, 'error');
    }
}

// 更新舒适指数
function updateComfortIndex(temp, hum) {
    let comfortLevel = '舒适';
    let comfortColor = '#28a745';
    
    if (temp > 28 || temp < 16) {
        comfortLevel = '不舒适';
        comfortColor = '#dc3545';
    } else if (hum > 80 || hum < 30) {
        comfortLevel = '一般';
        comfortColor = '#ffc107';
    }
    
    document.getElementById('comfortIndex').textContent = comfortLevel;
    document.getElementById('comfortIndex').style.color = comfortColor;
}

// 更新状态显示
function updateStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status status-${type}`;
}

// 空调控制
// 根据当前设备动态生成空调ID
function getACId() {
    const device = currentDevice || 'room1';
    return `ac_${device}`;
}

function setupACControls() {
    const acButtons = document.querySelectorAll('.ac-btn');
    const acStatus = document.getElementById('acStatus');
    
    // 加载初始空调状态
    loadACStatus();
    
    acButtons.forEach(button => {
        button.addEventListener('click', async () => {
            if (button.id === 'acOff') {
                // 关闭空调
                await controlAC(false, null);
            } else {
                const temp = button.getAttribute('data-temp');
                // 开启空调并设置温度
                await controlAC(true, parseFloat(temp));
            }
        });
    });
    
    // 定时刷新空调状态
    setInterval(loadACStatus, 5000);
}

// 加载空调状态
async function loadACStatus() {
    try {
        const acId = getACId();
        const response = await fetch(`${API_BASE}/ac/${acId}?_t=${Date.now()}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            cache: 'no-cache'
        });
        
        if (response.ok) {
            const state = await response.json();
            const acStatus = document.getElementById('acStatus');
            
            if (state.power) {
                acStatus.textContent = `运行中 (目标: ${state.target_temp}°C, 当前: ${state.current_temp}°C)`;
                acStatus.style.color = '#28a745';
            } else {
                acStatus.textContent = '已关闭';
                acStatus.style.color = '#dc3545';
            }
        }
    } catch (error) {
        console.error('加载空调状态失败:', error);
    }
}

// 控制空调
async function controlAC(power, targetTemp) {
    try {
        updateStatus('正在控制空调...', 'loading');
        
        const body = {
            power: power,
            device_id: currentDevice === 'all' ? 'room1' : currentDevice,
            mode: 'cool'
        };
        
        if (targetTemp !== null) {
            body.target_temp = targetTemp;
        }
        
        const acId = getACId();
        const response = await fetch(`${API_BASE}/ac/${acId}/control`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(body)
        });
        
        if (response.ok) {
            const result = await response.json();
            
            const acStatus = document.getElementById('acStatus');
            if (power) {
                acStatus.textContent = `运行中 (${targetTemp}°C)`;
                acStatus.style.color = '#28a745';
                updateStatus(`空调已设置为 ${targetTemp}°C`, 'success');
            } else {
                acStatus.textContent = '已关闭';
                acStatus.style.color = '#dc3545';
                updateStatus('空调已关闭', 'success');
            }
            
            // 刷新状态
            setTimeout(loadACStatus, 1000);
        } else {
            throw new Error('控制失败');
        }
    } catch (error) {
        console.error('控制空调失败:', error);
        updateStatus('控制空调失败', 'error');
    }
}

// 事件监听
document.getElementById('deviceSelect').addEventListener('change', (e) => {
    currentDevice = e.target.value;
    loadHistory(currentDevice);
    // 切换设备时也重新加载空调状态
    loadACStatus();
});

document.getElementById('refreshBtn').addEventListener('click', () => {
    loadHistory(currentDevice);
});

// 自动刷新（每10秒）
setInterval(() => {
    loadHistory(currentDevice);
}, 10000);

// 响应式图表
window.addEventListener('resize', () => {
    chart.resize();
});

// 初始化
loadDevices();
loadHistory();
setupACControls();