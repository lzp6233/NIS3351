
const API_BASE = 'http://localhost:5000';
const LOCK_ID = 'FRONT_DOOR';
// 刷新控制
let refreshInterval = 5000; // 默认5秒
let intervalId = null;
let realtimeMode = false;

// 更新锁状态显示
function updateLockStatusDisplay(lockData) {
    document.getElementById('lockId').textContent = lockData.lock_id;
    
    const statusElement = document.getElementById('lockStatus');
    statusElement.textContent = lockData.locked ? 'LOCKED' : 'UNLOCKED';
    statusElement.className = lockData.locked ? 'status-badge status-locked' : 'status-badge status-unlocked';
    
    document.getElementById('lockBattery').textContent = lockData.battery ? `${lockData.battery}%` : '--';
    document.getElementById('lockUpdated').textContent = lockData.updated_at ? 
        new Date(lockData.updated_at).toLocaleString('zh-CN') : '--';
}

// 切换认证字段显示
function toggleAuthFields() {
    const method = document.getElementById('unlockMethod').value;
    
    // 隐藏所有认证字段
    document.getElementById('pincodeFields').style.display = 'none';
    document.getElementById('faceFields').style.display = 'none';
    document.getElementById('fingerprintFields').style.display = 'none';
    document.getElementById('generalFields').style.display = 'none';
    
    // 显示对应的认证字段
    switch(method) {
        case 'PINCODE':
            document.getElementById('pincodeFields').style.display = 'block';
            break;
        case 'FACE':
            document.getElementById('faceFields').style.display = 'block';
            break;
        case 'FINGERPRINT':
            document.getElementById('fingerprintFields').style.display = 'block';
            break;
        case 'APP':
        case 'REMOTE':
            document.getElementById('generalFields').style.display = 'block';
            break;
    }
}

// 预览面部图像
function previewFaceImage() {
    const fileInput = document.getElementById('faceImageInput');
    const preview = document.getElementById('faceImagePreview');
    
    if (fileInput.files && fileInput.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.innerHTML = `<img src="${e.target.result}" alt="面部图像预览">`;
        };
        reader.readAsDataURL(fileInput.files[0]);
    }
}

// 生成模拟指纹数据
function generateFingerprint() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < 64; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    document.getElementById('fingerprintInput').value = result;
}

// 更新自动锁定配置
async function updateAutoLockConfig() {
    const enabled = document.getElementById('autoLockEnabled').checked;
    const delay = parseInt(document.getElementById('autoLockDelay').value);
    
    try {
        const res = await fetch(`${API_BASE}/locks/${LOCK_ID}/auto-lock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                auto_lock_enabled: enabled,
                auto_lock_delay: delay
            })
        });
        
        if (!res.ok) throw new Error('配置更新失败');
        
        alert('自动锁定配置已更新');
    } catch (error) {
        console.error('更新配置失败:', error);
        alert('配置更新失败，请检查网络连接');
    }
}

// 加载自动锁定配置
async function loadAutoLockConfig() {
    try {
        const res = await fetch(`${API_BASE}/locks/${LOCK_ID}/auto-lock`);
        if (!res.ok) throw new Error('配置加载失败');
        
        const config = await res.json();
        document.getElementById('autoLockEnabled').checked = config.auto_lock_enabled;
        document.getElementById('autoLockDelay').value = config.auto_lock_delay;
    } catch (error) {
        console.error('加载配置失败:', error);
    }
}

// 加载锁状态
async function loadLockState() {
    try {
        const res = await fetch(`${API_BASE}/locks/${LOCK_ID}/state?_t=${Date.now()}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            cache: 'no-cache'
        });
        if (!res.ok) throw new Error('锁状态获取失败');
        const lockData = await res.json();
        updateLockStatusDisplay(lockData);
    } catch (error) {
        console.error('加载锁状态失败:', error);
        alert('加载锁状态失败，请检查网络连接或服务器状态');
    }
}

// 发送锁命令
async function sendLockCommand(action) {
    const method = document.getElementById('unlockMethod').value;
    let body = { action, method };
    
    // 根据不同的认证方式构建请求体
    switch(method) {
        case 'PINCODE':
            const username = document.getElementById('usernameInput').value.trim();
            const password = document.getElementById('passwordInput').value.trim();
            const pin = document.getElementById('pinInput').value.trim();
            
            if (!username || !password || !pin) {
                alert('PINCODE方式需要填写用户名、密码和PIN码');
                return;
            }
            
            body.username = username;
            body.password = password;
            body.pin = pin;
            break;
            
        case 'FACE':
            const faceUsername = document.getElementById('faceUsernameInput').value.trim();
            const faceFile = document.getElementById('faceImageInput').files[0];
            
            if (!faceUsername || !faceFile) {
                alert('面部识别需要填写用户名和上传面部图像');
                return;
            }
            
            // 将图像转换为base64
            const faceImageData = await fileToBase64(faceFile);
            body.username = faceUsername;
            body.face_image = faceImageData;
            break;
            
        case 'FINGERPRINT':
            const fingerprintUsername = document.getElementById('fingerprintUsernameInput').value.trim();
            const fingerprintData = document.getElementById('fingerprintInput').value.trim();
            
            if (!fingerprintUsername || !fingerprintData) {
                alert('指纹识别需要填写用户名和指纹数据');
                return;
            }
            
            body.username = fingerprintUsername;
            body.fingerprint_data = fingerprintData;
            break;
            
        default:
            // 其他方式不支持（前端已经移除 APP/REMOTE）
            break;
    }
    
    try {
        const res = await fetch(`${API_BASE}/locks/${LOCK_ID}/command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.error || '命令发送失败');
        }
        
        const result = await res.json();
        alert(`门锁${action === 'lock' ? '上锁' : '解锁'}命令已发送\n${result.auth_detail || ''}`);
        
        // 稍后刷新状态
        setTimeout(loadLockState, 1000);
    } catch (error) {
        console.error('发送命令失败:', error);
        alert(`命令发送失败: ${error.message}`);
    }
}

// 将文件转换为base64
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            // 移除data:image/...;base64,前缀，只保留base64数据
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = error => reject(error);
    });
}

// 事件监听
document.getElementById('btnLock').addEventListener('click', () => sendLockCommand('lock'));
document.getElementById('btnUnlock').addEventListener('click', () => sendLockCommand('unlock'));

function setRefreshInterval(ms) {
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(loadLockState, ms);
}

function toggleRealtime() {
    realtimeMode = !realtimeMode;
    const btn = document.getElementById('btnRealtime');
    if (realtimeMode) {
        refreshInterval = 1000;
        btn.textContent = '实时更新：开启';
        btn.classList.add('active');
    } else {
        refreshInterval = 5000;
        btn.textContent = '实时更新：关闭';
        btn.classList.remove('active');
    }
    // 立即加载一次并重设定时
    loadLockState();
    setRefreshInterval(refreshInterval);
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadLockState();
    loadAutoLockConfig();
    toggleAuthFields(); // 初始化认证字段显示

    // 启动默认轮询
    setRefreshInterval(refreshInterval);

    // 实时按钮绑定
    const realtimeBtn = document.getElementById('btnRealtime');
    if (realtimeBtn) {
        realtimeBtn.addEventListener('click', toggleRealtime);
    }
});