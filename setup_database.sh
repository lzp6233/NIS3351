#!/bin/bash

# ============================================
# NIS3351 数据库一键初始化脚本
# 从 .env 文件读取配置
# ============================================

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 获取脚本所在目录（兼容 sh 和 bash）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || {
    echo "错误：无法切换到脚本所在目录"
    exit 1
}

echo -e "${GREEN}========================================"
echo "NIS3351 数据库初始化"
echo "========================================${NC}"
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ 未找到 .env 文件${NC}"
    echo ""
    echo "请先创建配置文件："
    echo "  1. cp .env.example .env"
    echo "  2. 编辑 .env 文件，填入你的数据库配置"
    echo ""
    read -p "是否现在创建 .env 文件? (y/n): " create_env
    
    if [ "$create_env" = "y" ] || [ "$create_env" = "Y" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ 已创建 .env 文件${NC}"
        echo "请编辑 .env 文件后重新运行此脚本"
        echo "  vi .env"
        exit 0
    else
        echo "退出"
        exit 1
    fi
fi

# 加载 .env 文件
echo -e "${YELLOW}加载配置文件...${NC}"
if [ -f ".env" ]; then
    set -a
    . ./.env
    set +a
    echo -e "${GREEN}✓ 配置已加载${NC}"
else
    echo -e "${RED}✗ 错误：.env 文件不存在${NC}"
    echo "当前目录: $(pwd)"
    echo "请确保在项目根目录下运行此脚本"
    exit 1
fi

# 显示配置信息（隐藏密码）
echo ""
echo "数据库配置："
echo "  主机: ${DB_HOST}"
echo "  端口: ${DB_PORT}"
echo "  数据库: ${DB_NAME}"
echo "  管理员: ${DB_ADMIN_USER}"
echo "  应用用户: ${DB_USER}"
echo ""

# 检查必需的配置
if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_ADMIN_USER" ]; then
    echo -e "${RED}错误: .env 文件中缺少必需的配置${NC}"
    echo "请检查 .env 文件，确保包含："
    echo "  DB_HOST, DB_PORT, DB_NAME, DB_ADMIN_USER, DB_ADMIN_PASSWORD"
    exit 1
fi

# 检查 gsql 是否可用
if ! command -v gsql &> /dev/null; then
    echo -e "${RED}错误: 找不到 gsql 命令${NC}"
    echo "请确保已配置环境变量："
    echo "  source ~/.bashrc"
    exit 1
fi

# 检查环境变量
echo -e "${YELLOW}步骤 1/3: 测试数据库连接...${NC}"
export PGPASSWORD="${DB_ADMIN_PASSWORD}"

if gsql -d postgres -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -W "${DB_ADMIN_PASSWORD}" -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 数据库连接成功${NC}"
else
    echo -e "${RED}✗ 数据库连接失败${NC}"
    echo "请检查："
    echo "  1. GaussDB 是否正在运行: ps -ef | grep gaussdb"
    echo "  2. .env 文件中的用户名和密码是否正确"
    echo "  3. 端口是否正确（${DB_PORT}）"
    echo ""
    echo "手动连接测试："
    echo "  gsql -d postgres -h ${DB_HOST} -p ${DB_PORT} -U ${DB_ADMIN_USER} -W ${DB_ADMIN_PASSWORD}"
    unset PGPASSWORD
    exit 1
fi

echo ""
echo -e "${YELLOW}步骤 2/4: 创建数据库和表...${NC}"

# 首先检查数据库是否存在，如果不存在则创建
if gsql -d postgres -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -W "${DB_ADMIN_PASSWORD}" -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" | grep -q 1; then
    echo -e "${GREEN}✓ 数据库 ${DB_NAME} 已存在${NC}"
else
    echo -e "${YELLOW}创建数据库 ${DB_NAME}...${NC}"
    gsql -d postgres -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -W "${DB_ADMIN_PASSWORD}" -c "CREATE DATABASE ${DB_NAME};" > /dev/null 2>&1
    echo -e "${GREEN}✓ 数据库创建成功${NC}"
fi

# 然后在 smart_home 数据库中创建表
echo -e "${YELLOW}创建数据表...${NC}"
if gsql -d "${DB_NAME}" -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -W "${DB_ADMIN_PASSWORD}" -f init_db.sql > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 数据表创建成功${NC}"
else
    echo -e "${YELLOW}⚠ 部分表可能已存在${NC}"
fi

echo ""
echo -e "${YELLOW}步骤 3/4: 配置用户权限...${NC}"

# 创建应用用户（如果不存在）
gsql -d postgres -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -W "${DB_ADMIN_PASSWORD}" << EOF > /dev/null 2>&1
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = '${DB_USER}') THEN
        CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
        RAISE NOTICE 'User ${DB_USER} created';
    END IF;
END
\$\$;
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
\c ${DB_NAME}
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${DB_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};
EOF

echo -e "${GREEN}✓ 用户权限配置完成${NC}"

echo ""
echo -e "${YELLOW}步骤 4/4: 初始化应用数据...${NC}"

# 检查 Python 虚拟环境
VENV_FOUND=0
if [ -d "venv" ]; then
    echo -e "${GREEN}✓ 找到虚拟环境 'venv'${NC}"
    source venv/bin/activate
    VENV_FOUND=1
elif [ -d "database" ]; then
    echo -e "${GREEN}✓ 找到虚拟环境 'database'${NC}"
    source database/bin/activate
    VENV_FOUND=1
elif [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}✓ 检测到已激活的虚拟环境: $VIRTUAL_ENV${NC}"
    VENV_FOUND=1
fi

if [ $VENV_FOUND -eq 0 ]; then
    echo -e "${YELLOW}⚠ 未找到 Python 虚拟环境，正在创建...${NC}"
    python3 -m venv database
    source database/bin/activate
    pip install -r requirements.txt > /dev/null 2>&1
    echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"
fi

# 运行初始化脚本
echo -e "${YELLOW}正在初始化空调数据...${NC}"
if python init_ac.py > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 空调数据初始化成功${NC}"
else
    echo -e "${RED}✗ 空调数据初始化失败${NC}"
    echo "请手动运行: python init_ac.py"
fi

# 初始化门锁用户
echo -e "${YELLOW}正在初始化门锁用户...${NC}"
if python init_lock_users.py > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 门锁用户初始化成功${NC}"
else
    echo -e "${RED}✗ 门锁用户初始化失败${NC}"
    echo "请手动运行: python init_lock_users.py"
fi

# 清理密码环境变量
unset PGPASSWORD

echo ""
echo -e "${GREEN}========================================"
echo "✓ 数据库初始化完成！"
echo "========================================${NC}"
echo ""
echo "数据库信息："
echo "  主机: ${DB_HOST}"
echo "  端口: ${DB_PORT}"
echo "  数据库: ${DB_NAME}"
echo "  用户: ${DB_USER}"
echo ""
echo "已创建的表："
echo "  - temperature_humidity_data (温湿度数据)"
echo "  - lock_state (门锁状态)"
echo "  - lock_events (门锁事件)"
echo "  - lock_users (门锁用户)"
echo "  - lock_auto_config (自动锁定配置)"
echo "  - ac_state (空调状态)"
echo "  - ac_events (空调事件)"
echo "  - lighting_state (灯具状态)"
echo "  - lighting_events (灯具事件)"
echo "  - smoke_alarm_state (烟雾报警器状态)"
echo "  - smoke_alarm_events (烟雾报警器事件)"
echo "  - rooms (房间管理)"
echo ""
echo "已初始化的房间："
echo "  - living (客厅)"
echo "  - bedroom1 (主卧)"
echo "  - bedroom2 (次卧)"
echo "  - kitchen (厨房)"
echo ""
echo "已初始化的设备："
echo "  空调: ac_living, ac_bedroom1, ac_bedroom2, ac_kitchen"
echo "  门锁: FRONT_DOOR"
echo "  灯具: light_living, light_bedroom1, light_bedroom2, light_kitchen"
echo "  烟雾报警器: smoke_living, smoke_bedroom1, smoke_bedroom2, smoke_kitchen"
echo ""
echo "下一步："
echo "  1. 启动系统: sh run.sh"
echo "  2. 访问前端: http://localhost:8000"
echo ""
echo "测试连接："
echo "  gsql -d ${DB_NAME} -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -W <password>"
