import paramiko

def fix_supervisor():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    config = """[program:grid-trading]
directory=/home/trading/grid-trading
command=python3 -m uvicorn src.server.app:app --host 0.0.0.0 --port 8000
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/grid-trading.err.log
stdout_logfile=/var/log/supervisor/grid-trading.log
environment=PYTHONPATH="/home/trading/grid-trading"
"""
    
    try:
        ssh.connect('47.113.144.26', username='root', password='Chc20090629')
        
        # 写入新的配置文件
        stdin, stdout, stderr = ssh.exec_command('cat > /etc/supervisor/conf.d/grid-trading.conf', get_pty=True)
        stdin.write(config)
        stdin.close()
        
        print("更新配置文件完成")
        
        # 重新加载配置
        stdin, stdout, stderr = ssh.exec_command('supervisorctl reread && supervisorctl update')
        print("\n重新加载配置:")
        print(stdout.read().decode())
        
        # 重启服务
        stdin, stdout, stderr = ssh.exec_command('supervisorctl restart grid-trading')
        print("\n重启服务:")
        print(stdout.read().decode())
        
        # 检查状态
        stdin, stdout, stderr = ssh.exec_command('supervisorctl status')
        print("\n服务状态:")
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        ssh.close()

if __name__ == '__main__':
    fix_supervisor() 