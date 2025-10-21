
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
        const response = await fetch(`${API_BASE}/devices?_t=${Date.now()}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            cache: 'no-cache'
        });
        const devices = await response.json();
        
        const select = document.getElementById('deviceSelect');
        select.innerHTML = '<option value="all">所有设备</option>';
        
        devices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.device_id;
            option.textContent = `${device.device_id} (${device.data_count} 条数据)`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('加载设备列表失败:', error);
        updateStatus('加载设备失败', 'error');
    }
}

// 加载历史数据
async function loadHistory(deviceId = 'all') {
    try {
        updateStatus('加载中...', 'loading');
        
        const url = deviceId === 'all' 
            ? `${API_BASE}/history?limit=50&_t=${Date.now()}`
            : `${API_BASE}/history/${deviceId}?limit=50&_t=${Date.now()}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            cache: 'no-cache'
        });
        const data = await response.json();
        
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
        
        updateStatus('数据加载成功', 'success');
        
    } catch (error) {
        console.error('加载数据失败:', error);
        updateStatus('加载数据失败', 'error');
    }
}

// 更新状态显示
function updateStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status status-${type}`;
}

// 事件监听
document.getElementById('deviceSelect').addEventListener('change', (e) => {
    currentDevice = e.target.value;
    loadHistory(currentDevice);
});

document.getElementById('refreshBtn').addEventListener('click', () => {
    loadHistory(currentDevice);
});

// 跳转到门锁页面
document.getElementById('doorLockBtn').addEventListener('click', () => {
    window.location.href = 'door-lock.html';
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