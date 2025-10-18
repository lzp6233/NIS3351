-- ============================================
-- 创建数据库用户脚本（可选）
-- 使用方法：gsql -d postgres -h 127.0.0.1 -p 7654 -f create_user.sql
-- 需要使用管理员账户（如 opengauss）执行
-- ============================================

-- 检查用户是否已存在
SELECT 'Checking if user exists...' AS status;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'lzp') THEN
        CREATE USER lzp WITH PASSWORD 'Liuzipeng6233';
        RAISE NOTICE 'User lzp created successfully';
    ELSE
        RAISE NOTICE 'User lzp already exists';
    END IF;
END
$$;

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE smart_home TO lzp;
GRANT ALL PRIVILEGES ON DATABASE postgres TO lzp;

-- 连接到 smart_home 数据库并授予表权限
\c smart_home

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lzp;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO lzp;

-- 显示用户信息
SELECT 'User information:' AS status;
\du lzp

SELECT '✓ User setup completed!' AS status;

