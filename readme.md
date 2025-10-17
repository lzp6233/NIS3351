# NIS3351 项目

## 环境配置说明

### macOS / Linux 系统

#### 1. 创建虚拟环境
```bash
cd /path/to/NIS3351
python3 -m venv venv
```

#### 2. 激活虚拟环境
```bash
source venv/bin/activate
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```

#### 4. 退出虚拟环境（使用完毕后）
```bash
deactivate
```

---

### Windows 系统

#### 1. 创建虚拟环境
```bash
cd \path\to\NIS3351
python -m venv venv
```

#### 2. 激活虚拟环境
```bash
# 使用 CMD
venv\Scripts\activate.bat

# 使用 PowerShell
venv\Scripts\Activate.ps1
```

**注意**：如果 PowerShell 执行策略报错，需要先运行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```

#### 4. 退出虚拟环境（使用完毕后）
```bash
deactivate
```

---

## 重要提示

⚠️ **虚拟环境不能跨平台使用！**

- `venv` 文件夹已添加到 `.gitignore`，不会提交到版本控制
- 每个开发者需要在自己的系统上创建独立的虚拟环境
- 只需共享 `requirements.txt` 文件即可

## 项目依赖

主要依赖包括：
- Flask 2.3.3
- Flask-SocketIO 5.5.1
- paho-mqtt 1.6.1
- psycopg2-binary 2.9.9