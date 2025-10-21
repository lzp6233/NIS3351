
const API_BASE = 'http://localhost:5000';
const LOCK_ID = 'FRONT_DOOR';

// 更新锁状态显示
function updateLockStatusDisplay(lockData) {
    document.getElementById('lockId').textContent = lockData.lock_id;
    
    const statusElement = document.getElementById('lockStatus');
    statusElement.textContent = lockData.locked ? 'LOCKED' : 'UNLOCKED';
    statusElement.className = lockData.locked ? 'status-badge status-locked' : 'status-badge status-unlocked';
    
    document.getElementById('lockMethod').textContent = lockData.method || '--';
    document.getElementById('lockActor').textContent = lockData.actor || '--';
    document.getElementById('lockBattery').textContent = lockData.battery ? `${lockData.battery}%` : '--';
    document.getElementById('lockUpdated').textContent = lockData.updated_at ? 
        new Date(lockData.updated_at).toLocaleString('zh-CN') : '--';
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
    const pin = document.getElementById('pinInput').value.trim() || undefined;
    const actor = document.getElementById('actorInput').value.trim() || 'AppUser';
    
    // 验证PIN码（如果使用PINCODE方式）
    if (method === 'PINCODE' && (!pin || pin.length < 4)) {
        alert('PINCODE方式需要输入至少4位PIN码');
        return;
    }
    
    const body = { action, method, actor };
    if (method === 'PINCODE' && pin) body.pin = pin;
    
    try {
        const res = await fetch(`${API_BASE}/locks/${LOCK_ID}/command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        if (!res.ok) throw new Error('命令发送失败');
        
        const result = await res.json();
        alert(`门锁${action === 'lock' ? '上锁' : '解锁'}命令已发送`);
        
        // 稍后刷新状态
        setTimeout(loadLockState, 1000);
    } catch (error) {
        console.error('发送命令失败:', error);
        alert('命令发送失败，请检查网络连接');
    }
}

// 事件监听
document.getElementById('btnLock').addEventListener('click', () => sendLockCommand('lock'));
document.getElementById('btnUnlock').addEventListener('click', () => sendLockCommand('unlock'));
document.getElementById('refreshLock').addEventListener('click', loadLockState);

// 定时刷新锁状态（每10秒）
setInterval(loadLockState, 10000);

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', loadLockState);