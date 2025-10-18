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

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

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
    
    if [[ "$create_env" =~ ^[Yy]$ ]]; then
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
set -a
source .env
set +a
echo -e "${GREEN}✓ 配置已加载${NC}"

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

if gsql -d postgres -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 数据库连接成功${NC}"
else
    echo -e "${RED}✗ 数据库连接失败${NC}"
    echo "请检查："
    echo "  1. GaussDB 是否正在运行: ps -ef | grep gaussdb"
    echo "  2. .env 文件中的用户名和密码是否正确"
    echo "  3. 端口是否正确（${DB_PORT}）"
    echo ""
    echo "手动连接测试："
    echo "  gsql -d postgres -h ${DB_HOST} -p ${DB_PORT} -U ${DB_ADMIN_USER}"
    unset PGPASSWORD
    exit 1
fi

echo ""
echo -e "${YELLOW}步骤 2/3: 创建数据库和表...${NC}"
if gsql -d postgres -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -f init_db.sql 2>&1 | grep -v "already exists"; then
    echo -e "${GREEN}✓ 数据库和表创建成功${NC}"
else
    echo -e "${YELLOW}⚠ 数据库可能已存在${NC}"
fi

echo ""
echo -e "${YELLOW}步骤 3/3: 配置用户权限...${NC}"

# 创建应用用户（如果不存在）
gsql -d postgres -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" << EOF > /dev/null 2>&1
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
echo "  表: temperature_humidity_data"
echo ""
echo "下一步："
echo "  1. 配置已自动从 .env 文件读取"
echo "  2. 启动系统: ./run.sh"
echo ""
echo "测试连接："
echo "  gsql -d ${DB_NAME} -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER}"
