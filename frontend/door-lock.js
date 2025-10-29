
const API_BASE = 'http://localhost:5000';
const LOCK_ID = 'FRONT_DOOR';

let refreshInterval = 1000; 
let intervalId = null;
let realtimeMode = false;
let statusUpdateInterval = 1000; // 状态更新间隔1秒
let statusIntervalId = null;

// 全局错误处理 - 只alert一次
let hasShownConnectionError = false;

// 全局错误处理函数
function handleConnectionError(error, context = '') {
    console.error(`连接错误 ${context}:`, error);
    
    // 只在第一次出现连接错误时显示弹窗
    if (!hasShownConnectionError) {
        hasShownConnectionError = true;
        showPopup('无法连接到后端服务，请检查服务器是否正常运行', { type: 'error', title: '连接错误' });
        
        // 5分钟后重置错误标志，允许再次提示
        setTimeout(() => {
            hasShownConnectionError = false;
        }, 5 * 60 * 1000);
    }
}

// 居中弹窗与确认对话框
let popupTimer = null;

function ensurePopupDom() {
    if (document.getElementById('popupBackdrop')) return true;
    const create = () => {
        if (document.getElementById('popupBackdrop')) return true;
        const backdrop = document.createElement('div');
        backdrop.id = 'popupBackdrop';
        backdrop.className = 'popup-backdrop';
        backdrop.setAttribute('role', 'dialog');
        backdrop.setAttribute('aria-hidden', 'true');
        backdrop.innerHTML = `
          <div id="popup" class="popup popup-info" role="document">
            <div id="popupTitle" class="popup-title">提示</div>
            <div id="popupMessage" class="popup-message"></div>
            <div id="popupActions" class="popup-actions">
              <button id="popupCloseBtn" class="popup-btn" type="button">知道了</button>
            </div>
          </div>`;
        (document.body || document.documentElement).appendChild(backdrop);
        return true;
    };
    if (document.readyState === 'loading' && !document.body) {
        document.addEventListener('DOMContentLoaded', create, { once: true });
        return false;
    }
    return create();
}

function showDialog({ title = '提示', message = '', type = 'info', buttons = [], autoCloseMs }) {
    const ready = ensurePopupDom();
    if (!ready) {
        return new Promise((resolve) => {
            const retry = () => {
                showDialog({ title, message, type, buttons, autoCloseMs }).then(resolve);
            };
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', retry, { once: true });
            } else {
                setTimeout(retry, 0);
            }
        });
    }
    const backdrop = document.getElementById('popupBackdrop');
    const popup = document.getElementById('popup');
    const titleEl = document.getElementById('popupTitle');
    const messageEl = document.getElementById('popupMessage');
    const actionsEl = document.getElementById('popupActions');

    if (!backdrop || !popup || !titleEl || !messageEl || !actionsEl) {
        // 再尝试一次创建并查询
        setTimeout(ensurePopupDom, 0);
        setTimeout(() => {}, 0);
        const b2 = document.getElementById('popupBackdrop');
        const p2 = document.getElementById('popup');
        const t2 = document.getElementById('popupTitle');
        const m2 = document.getElementById('popupMessage');
        const a2 = document.getElementById('popupActions');
        if (!b2 || !p2 || !t2 || !m2 || !a2) {
            // 最后兜底：不再使用浏览器 alert，改为简单 DOM 注入
            const div = document.createElement('div');
            div.style.position = 'fixed';
            div.style.inset = '0';
            div.style.background = 'rgba(0,0,0,0.35)';
            div.style.display = 'flex';
            div.style.alignItems = 'center';
            div.style.justifyContent = 'center';
            div.style.zIndex = '3000';
            div.innerHTML = `<div style="min-width:280px;max-width:520px;background:#fff;border-radius:12px;padding:16px 18px;font-family:inherit;">
                <div style=\"font-weight:600;margin-bottom:6px;color:#2b4a8a;\">${title}</div>
                <div style=\"color:#333;line-height:1.6;\">${message}</div>
                <div style=\"text-align:right;margin-top:12px;\"><button id=\"tmpClose\" style=\"padding:6px 12px;border:none;border-radius:8px;background:#2b4a8a;color:#fff;\">知道了</button></div>
            </div>`;
            (document.body || document.documentElement).appendChild(div);
            return new Promise((resolve)=>{
                div.querySelector('#tmpClose').addEventListener('click', ()=>{ div.remove(); resolve(true); });
            });
        }
    }

    // 样式与内容
    popup.classList.remove('popup-info', 'popup-success', 'popup-error');
    popup.classList.add(`popup-${type}`);
    titleEl.textContent = title;
    messageEl.textContent = message;

    // 渲染按钮
    actionsEl.innerHTML = '';
    const disposers = [];
    const close = (value) => {
        backdrop.style.display = 'none';
        disposers.forEach(fn => fn());
        if (popupTimer) { clearTimeout(popupTimer); popupTimer = null; }
        resolver && resolver(value);
    };

    let resolver;
    const p = new Promise((resolve) => { resolver = resolve; });

    const onBackdropClick = (e) => { if (e.target === backdrop) close(true); };
    backdrop.addEventListener('click', onBackdropClick);
    disposers.push(() => backdrop.removeEventListener('click', onBackdropClick));

    if (!buttons || buttons.length === 0) {
        buttons = [{ text: '知道了', value: true, primary: true }];
    }
    buttons.forEach((btn) => {
        const b = document.createElement('button');
        b.className = 'popup-btn';
        b.textContent = btn.text;
        if (btn.primary && type === 'error') {
            // 错误时也保持主按钮样式一致
        }
        const onClick = () => close(btn.value);
        b.addEventListener('click', onClick);
        disposers.push(() => b.removeEventListener('click', onClick));
        actionsEl.appendChild(b);
    });

    backdrop.style.display = 'flex';

    const duration = typeof autoCloseMs === 'number' ? autoCloseMs : (type === 'error' ? 0 : 2200);
    if (duration > 0 && buttons.length === 1) {
        popupTimer = setTimeout(() => close(true), duration);
    }

    return p;
}

function showPopup(message, options = {}) {
    const { type = 'info', title = '提示', autoCloseMs } = options;
    return showDialog({ title, message, type, autoCloseMs });
}

function showConfirm(message, { title = '确认操作', type = 'info' } = {}) {
    return showDialog({
        title,
        message,
        type,
        buttons: [
            { text: '取消', value: false },
            { text: '确定', value: true, primary: true }
        ],
        autoCloseMs: 0
    });
}

function hidePopup() {
    const backdrop = document.getElementById('popupBackdrop');
    if (backdrop) backdrop.style.display = 'none';
}

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

// 启动状态更新定时器
function startStatusUpdate() {
    if (statusIntervalId) clearInterval(statusIntervalId);
    statusIntervalId = setInterval(loadLockState, statusUpdateInterval);
}

// 停止状态更新定时器
function stopStatusUpdate() {
    if (statusIntervalId) {
        clearInterval(statusIntervalId);
        statusIntervalId = null;
    }
}

// 清空所有输入框
function clearAllInputs() {
    // 清空PINCODE输入
    document.getElementById('pinInput').value = '';
    
    // 清空面部识别输入
    document.getElementById('faceImageInput').value = '';
    document.getElementById('faceImagePreview').innerHTML = '';
    
    // 清空指纹识别输入
    document.getElementById('fingerprintUsernameInput').value = '';
    document.getElementById('fingerprintPasswordInput').value = '';
    
    // 清空通用输入
    document.getElementById('actorInput').value = '';
}

// 加载用户列表
async function loadUserList() {
    try {
        const res = await fetch(`${API_BASE}/locks/users`);
        if (!res.ok) throw new Error('获取用户列表失败');
        
        const data = await res.json();
        const userList = document.getElementById('userList');
        
        // 清空现有选项（保留默认选项）
        userList.innerHTML = '<option value="">选择要注销的用户</option>';
        
        // 添加用户选项
        data.users.forEach(username => {
            const option = document.createElement('option');
            option.value = username;
            option.textContent = username;
            userList.appendChild(option);
        });
    } catch (error) {
        handleConnectionError(error, '加载用户列表');
    }
}

// 注销用户
async function logoutUser() {
    console.log('注销函数被调用');
    
    const userList = document.getElementById('userList');
    const selectedUser = userList.value;
    const password = document.getElementById('deletePassword').value.trim();
    
    console.log('选择的用户:', selectedUser);
    console.log('输入的密码:', password ? '已填写' : '未填写');
    
    if (!selectedUser) {
        showPopup('请选择要注销的用户', { type: 'error', title: '参数缺失' });
        return;
    }
    
    if (!password) {
        showPopup('请输入要注销用户的密码进行验证', { type: 'error', title: '参数缺失' });
        return;
    }
    
    const ok = await showConfirm(`确定要注销用户 "${selectedUser}" 吗？此操作不可撤销。`, { title: '请确认', type: 'error' });
    if (!ok) return;
    
    try {
    
        console.log('正在发送注销请求...', { password: password });
        const res = await fetch(`${API_BASE}/locks/users/${selectedUser}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password })
        });
        
        console.log('注销响应状态:', res.status);
        
        if (!res.ok) {
            const errorData = await res.json();
            console.error('注销失败:', errorData);
            throw new Error(errorData.error || '注销用户失败');
        }
        
        const result = await res.json();
        console.log('注销成功:', result);
        showPopup(`用户 "${selectedUser}" 已成功注销`, { type: 'success', title: '注销成功' });
        
        // 清空密码输入框
        document.getElementById('deletePassword').value = '';
        
        // 重新加载用户列表
        loadUserList();
        
    } catch (error) {
        console.error('注销用户失败:', error);
        showPopup(`注销用户失败: ${error.message}`, { type: 'error', title: '操作失败' });
    }
}

// 切换认证字段显示
function toggleAuthFields() {
    const method = document.getElementById('unlockMethod').value;
    
    // 隐藏所有认证字段
    document.getElementById('pincodeFields').style.display = 'none';
    document.getElementById('faceFields').style.display = 'none';
    document.getElementById('fingerprintFields').style.display = 'none';
    document.getElementById('generalFields').style.display = 'none';
    
    // 隐藏所有管理区域
    document.getElementById('registerSection').style.display = 'none';
    document.getElementById('changePinSection').style.display = 'none';
    document.getElementById('userManageSection').style.display = 'none';
    
    // 重置按钮文本
    document.getElementById('toggleRegisterBtn').textContent = '➕ 注册新用户';
    document.getElementById('toggleChangePinBtn').textContent = '🔑 修改PINCODE';
    document.getElementById('toggleUserManageBtn').textContent = '👥 用户管理';
    
    // 显示对应的认证字段和管理区域
    switch(method) {
        case 'PINCODE':
            document.getElementById('pincodeFields').style.display = 'block';
            // PINCODE模式只显示修改PINCODE按钮
            document.getElementById('toggleChangePinBtn').style.display = 'inline-block';
            document.getElementById('toggleRegisterBtn').style.display = 'none';
            document.getElementById('toggleUserManageBtn').style.display = 'none';
            break;
        case 'FACE':
            document.getElementById('faceFields').style.display = 'block';
            // 面部模式显示注册用户和用户管理按钮
            document.getElementById('toggleRegisterBtn').style.display = 'inline-block';
            document.getElementById('toggleUserManageBtn').style.display = 'inline-block';
            document.getElementById('toggleChangePinBtn').style.display = 'none';
            break;
        case 'FINGERPRINT':
            document.getElementById('fingerprintFields').style.display = 'block';
            // 指纹模式显示注册用户和用户管理按钮
            document.getElementById('toggleRegisterBtn').style.display = 'inline-block';
            document.getElementById('toggleUserManageBtn').style.display = 'inline-block';
            document.getElementById('toggleChangePinBtn').style.display = 'none';
            break;
        case 'APP':
        case 'REMOTE':
            document.getElementById('generalFields').style.display = 'block';
            // 其他模式隐藏管理按钮
            document.getElementById('toggleRegisterBtn').style.display = 'none';
            document.getElementById('toggleUserManageBtn').style.display = 'none';
            document.getElementById('toggleChangePinBtn').style.display = 'none';
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
    const delay = parseInt(document.getElementById('autoLockDelay').value);
    
    if (!delay || delay < 1 || delay > 60) {
        showPopup('延迟时间必须在1-60秒之间', { type: 'error', title: '参数错误' });
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/locks/${LOCK_ID}/auto-lock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                auto_lock_enabled: true,  // 总是启用自动锁定
                auto_lock_delay: delay
            })
        });
        
        if (!res.ok) throw new Error('配置更新失败');
        
        showPopup(`自动锁定配置已更新：解锁后${delay}秒自动上锁`, { type: 'success', title: '更新成功' });
    } catch (error) {
        console.error('更新配置失败:', error);
        showPopup('配置更新失败，请检查网络连接', { type: 'error', title: '更新失败' });
    }
}

// 加载自动锁定配置
async function loadAutoLockConfig() {
    try {
        const res = await fetch(`${API_BASE}/locks/${LOCK_ID}/auto-lock`);
        if (!res.ok) throw new Error('配置加载失败');
        
        const config = await res.json();
        document.getElementById('autoLockDelay').value = config.auto_lock_delay || 5;
    } catch (error) {
        handleConnectionError(error, '加载自动锁定配置');
        // 使用默认值
        document.getElementById('autoLockDelay').value = 5;
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
        handleConnectionError(error, '加载锁状态');
    }
}

// 发送锁命令
async function sendLockCommand(action) {
    const method = document.getElementById('unlockMethod').value;
    let body = { action, method };
    
    // 根据不同的认证方式构建请求体
    switch(method) {
        case 'PINCODE':
            const pin = document.getElementById('pinInput').value.trim();
            
            if (!pin) {
                showPopup('PINCODE方式需要填写PIN码', { type: 'error', title: '参数缺失' });
                return;
            }
            
            body.pin = pin;
            break;
            
        case 'FACE':
            const faceFile = document.getElementById('faceImageInput').files[0];
            
            if (!faceFile) {
                showPopup('面部识别需要上传面部图像', { type: 'error', title: '参数缺失' });
                return;
            }
            
            // 将图像转换为base64
            const faceImageData = await fileToBase64(faceFile);
            body.face_image = faceImageData;
            break;
            
        case 'FINGERPRINT':
            const fingerprintUsername = document.getElementById('fingerprintUsernameInput').value.trim();
            const fingerprintPassword = document.getElementById('fingerprintPasswordInput').value.trim();
            
            if (!fingerprintUsername || !fingerprintPassword) {
                showPopup('指纹识别需要填写用户名和密码', { type: 'error', title: '参数缺失' });
                return;
            }
            
            body.username = fingerprintUsername;
            body.password = fingerprintPassword;
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
        showPopup(`门锁${action === 'lock' ? '上锁' : '解锁'}命令已发送\n${result.auth_detail || ''}`, { type: 'success', title: '已发送' });
        
        // 清空所有输入框
        clearAllInputs();
        
        // 稍后刷新状态
        setTimeout(loadLockState, 1000);
    } catch (error) {
        console.error('发送命令失败:', error);
        showPopup(`命令发送失败: ${error.message}`, { type: 'error', title: '发送失败' });
        
        // 即使失败也清空输入框
        clearAllInputs();
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
        refreshInterval = 500; // 实时模式500ms
        btn.textContent = '实时更新：开启';
        btn.classList.add('active');
    } else {
        refreshInterval = 1000; // 普通模式1秒
        btn.textContent = '实时更新：关闭';
        btn.classList.remove('active');
    }
    // 立即加载一次并重设定时
    loadLockState();
    setRefreshInterval(refreshInterval);
}

// 预览注册用户的面部图像
function previewRegFace() {
    const fileInput = document.getElementById('regFaceInput');
    const preview = document.getElementById('regFacePreview');
    
    if (fileInput.files && fileInput.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.innerHTML = `<img src="${e.target.result}" alt="面部图像预览">`;
        };
        reader.readAsDataURL(fileInput.files[0]);
    }
}

// 注册新用户
async function registerUser() {
    console.log('注册函数被调用');
    
    const username = document.getElementById('regUsername').value.trim();
    const password = document.getElementById('regPassword').value.trim();
    const faceFile = document.getElementById('regFaceInput').files[0];
    
    console.log('用户名:', username);
    console.log('密码:', password ? '已填写' : '未填写');
    console.log('面部图像:', faceFile ? '已选择' : '未选择');
    
    if (!username || !password) {
        showPopup('用户名和密码是必填项', { type: 'error', title: '参数缺失' });
        return;
    }
    
    let body = {
        username: username,
        password: password
    };
    
    // 处理面部图像
    if (faceFile) {
        try {
            console.log('正在处理面部图像...');
            const faceImageData = await fileToBase64(faceFile);
            body.face_image = faceImageData;
            console.log('面部图像处理完成');
        } catch (error) {
            console.error('面部图像处理失败:', error);
            showPopup('面部图像处理失败', { type: 'error', title: '处理失败' });
            return;
        }
    }
    
    try {
        console.log('正在发送注册请求...', body);
        const res = await fetch(`${API_BASE}/locks/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        console.log('注册响应状态:', res.status);
        
        if (!res.ok) {
            const errorData = await res.json();
            console.error('注册失败:', errorData);
            throw new Error(errorData.error || '注册失败');
        }
        
        const result = await res.json();
        console.log('注册成功:', result);
        showPopup(`用户 ${result.username} 注册成功！`, { type: 'success', title: '注册成功' });
        
        // 清空表单
        document.getElementById('regUsername').value = '';
        document.getElementById('regPassword').value = '';
        document.getElementById('regFaceInput').value = '';
        document.getElementById('regFacePreview').innerHTML = '';
        
        // 隐藏注册区域
        document.getElementById('registerSection').style.display = 'none';
        document.getElementById('toggleRegisterBtn').textContent = '➕ 注册新用户';
        
    } catch (error) {
        console.error('注册失败:', error);
        showPopup(`注册失败: ${error.message}`, { type: 'error', title: '注册失败' });
    }
}

// 修改PINCODE
async function changePincode() {
    const currentPin = document.getElementById('currentPin').value.trim();
    const newPin = document.getElementById('newPin').value.trim();
    const confirmPin = document.getElementById('confirmPin').value.trim();
    
    if (!currentPin || !newPin || !confirmPin) {
        showPopup('请填写所有字段', { type: 'error', title: '参数缺失' });
        return;
    }
    
    if (newPin !== confirmPin) {
        showPopup('新PINCODE和确认PINCODE不一致', { type: 'error', title: '校验失败' });
        return;
    }
    
    if (newPin.length < 4) {
        showPopup('新PINCODE长度至少4位', { type: 'error', title: '格式不正确' });
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/locks/pincode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_pin: currentPin,
                new_pin: newPin
            })
        });
        
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.error || '修改PINCODE失败');
        }
        
        const result = await res.json();
        showPopup('PINCODE修改成功！', { type: 'success', title: '修改成功' });
        
        // 清空表单
        document.getElementById('currentPin').value = '';
        document.getElementById('newPin').value = '';
        document.getElementById('confirmPin').value = '';
        
        // 隐藏修改PINCODE区域
        document.getElementById('changePinSection').style.display = 'none';
        document.getElementById('toggleChangePinBtn').textContent = '🔑 修改PINCODE';
        
    } catch (error) {
        console.error('修改PINCODE失败:', error);
        showPopup(`修改PINCODE失败: ${error.message}`, { type: 'error', title: '修改失败' });
    }
}


// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadLockState();
    loadAutoLockConfig();
    toggleAuthFields(); // 初始化认证字段显示

    // 启动默认轮询
    setRefreshInterval(refreshInterval);
    
    // 启动状态更新定时器（每5秒更新一次）
    startStatusUpdate();

    // 实时按钮绑定
    const realtimeBtn = document.getElementById('btnRealtime');
    if (realtimeBtn) {
        realtimeBtn.addEventListener('click', toggleRealtime);
    }
    
    // 注册按钮绑定
    const registerBtn = document.getElementById('btnRegister');
    if (registerBtn) {
        console.log('找到注册按钮，绑定事件');
        registerBtn.addEventListener('click', registerUser);
    } else {
        console.error('未找到注册按钮！');
    }
    
    // 切换注册区域显示
    const toggleRegisterBtn = document.getElementById('toggleRegisterBtn');
    if (toggleRegisterBtn) {
        toggleRegisterBtn.addEventListener('click', function() {
            const registerSection = document.getElementById('registerSection');
            if (registerSection.style.display === 'none') {
                registerSection.style.display = 'block';
                toggleRegisterBtn.textContent = '➖ 取消注册';
            } else {
                registerSection.style.display = 'none';
                toggleRegisterBtn.textContent = '➕ 注册新用户';
            }
        });
    }
    
    // 修改PINCODE按钮绑定
    const changePinBtn = document.getElementById('btnChangePin');
    if (changePinBtn) {
        changePinBtn.addEventListener('click', changePincode);
    }
    
    // 切换修改PINCODE区域显示
    const toggleChangePinBtn = document.getElementById('toggleChangePinBtn');
    if (toggleChangePinBtn) {
        toggleChangePinBtn.addEventListener('click', function() {
            const changePinSection = document.getElementById('changePinSection');
            if (changePinSection.style.display === 'none') {
                changePinSection.style.display = 'block';
                toggleChangePinBtn.textContent = '➖ 取消修改';
            } else {
                changePinSection.style.display = 'none';
                toggleChangePinBtn.textContent = '🔑 修改PINCODE';
            }
        });
    }
    
    // 用户管理按钮绑定
    const logoutUserBtn = document.getElementById('btnLogoutUser');
    if (logoutUserBtn) {
        console.log('找到注销按钮，绑定事件');
        logoutUserBtn.addEventListener('click', logoutUser);
    } else {
        console.error('未找到注销按钮！');
    }
    
    // 切换用户管理区域显示
    const toggleUserManageBtn = document.getElementById('toggleUserManageBtn');
    if (toggleUserManageBtn) {
        toggleUserManageBtn.addEventListener('click', function() {
            const userManageSection = document.getElementById('userManageSection');
            if (userManageSection.style.display === 'none') {
                userManageSection.style.display = 'block';
                toggleUserManageBtn.textContent = '➖ 取消管理';
                // 加载用户列表
                loadUserList();
            } else {
                userManageSection.style.display = 'none';
                toggleUserManageBtn.textContent = '👥 用户管理';
            }
        });
    }
});