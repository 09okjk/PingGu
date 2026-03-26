import psycopg
import sys
import os

# 设置输出编码为 UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from env_loader import load_env_file, get_bool_env, get_env

# 加载 .env 文件
load_env_file()

host = get_env('PINGGU_DB_HOST', '192.168.124.126')
port = int(get_env('PINGGU_DB_PORT', '5432'))
database = get_env('PINGGU_DB_NAME', 'pinggu_dev')
user = get_env('PINGGU_DB_USER', 'postgres')
password = get_env('PINGGU_DB_PASSWORD', 'wk888')

print(f"Connecting to: {host}:{port}/{database} as {user}", flush=True)

try:
    # 使用 psycopg v3 连接
    conn = psycopg.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password
    )
    print("[OK] Database connection successful!", flush=True)
    
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"PostgreSQL version: {version[0][:50]}...", flush=True)
    
    # 检查是否有需要的表
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    print(f"Tables in database: {[t[0] for t in tables]}", flush=True)
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"[ERROR] Connection failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
