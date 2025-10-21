# 配置文件模板

## 创建配置文件

在项目根目录创建 `.env` 文件，内容如下：

```env
# ============================================
# NIS3351 智慧家居系统配置文件
# ============================================

# ============================================
# 数据库配置 (openGauss)
# ============================================

# 数据库主机地址
DB_HOST=127.0.0.1

# 数据库端口（openGauss/GaussDB 默认 7654）
DB_PORT=7654

# 数据库名称
DB_NAME=smart_home

# 管理员用户（用于初始化数据库，通常是 opengauss 或 gaussdb）
DB_ADMIN_USER=opengauss

# 管理员密码
DB_ADMIN_PASSWORD=your_admin_password_here

# 应用用户（日常使用）
DB_USER=nis3351_user

# 应用用户密码
DB_PASSWORD=your_user_password_here


# ============================================
# MQTT 配置
# ============================================

# MQTT Broker 地址
MQTT_BROKER=localhost

# MQTT Broker 端口（默认 1883）
MQTT_PORT=1883
```

## 配置说明

### 数据库配置

- **DB_HOST**: openGauss/GaussDB 数据库的主机地址，通常是 `127.0.0.1`
- **DB_PORT**: openGauss/GaussDB 默认端口是 `7654`
- **DB_NAME**: 数据库名称，建议使用 `smart_home` 或 `nis3351`
- **DB_ADMIN_USER**: 管理员用户名，通常是 `opengauss` 或 `gaussdb`
- **DB_ADMIN_PASSWORD**: 管理员密码，请替换为你的实际密码
- **DB_USER**: 应用用户名，建议使用 `nis3351_user`
- **DB_PASSWORD**: 应用用户密码，请设置一个强密码

### MQTT 配置

- **MQTT_BROKER**: MQTT Broker 地址，通常是 `localhost`
- **MQTT_PORT**: MQTT Broker 端口，默认是 `1883`

## 快速配置步骤

1. 复制配置模板：
   ```bash
   cat > .env << 'EOF'
   DB_HOST=127.0.0.1
   DB_PORT=7654
   DB_NAME=smart_home
   DB_ADMIN_USER=opengauss
   DB_ADMIN_PASSWORD=替换为你的密码
   DB_USER=nis3351_user
   DB_PASSWORD=替换为你的密码
   MQTT_BROKER=localhost
   MQTT_PORT=1883
   EOF
   ```

2. 编辑配置文件：
   ```bash
   vi .env
   ```

3. 替换密码后保存退出

4. 运行初始化脚本：
   ```bash
   sh setup_database.sh
   ```

## 安全提示

⚠️ **重要**：
- 不要将 `.env` 文件提交到 Git 仓库
- 使用强密码
- 在生产环境中限制数据库访问权限

