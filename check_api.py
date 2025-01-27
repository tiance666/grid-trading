import paramiko

def check_api():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect('47.113.144.26', username='root', password='Chc20090629')
        
        # 检查app.py的内容
        stdin, stdout, stderr = ssh.exec_command('cat /home/trading/grid-trading/src/server/app.py')
        print("API配置:")
        print(stdout.read().decode())
        
        # 检查CORS配置
        stdin, stdout, stderr = ssh.exec_command('grep -r "CORSMiddleware" /home/trading/grid-trading/src/server/')
        print("\nCORS配置:")
        print(stdout.read().decode())
        
        # 检查API路由
        stdin, stdout, stderr = ssh.exec_command('grep -r "@app.post" /home/trading/grid-trading/src/server/')
        print("\nAPI路由:")
        print(stdout.read().decode())
        
        # 检查服务日志
        stdin, stdout, stderr = ssh.exec_command('tail -n 50 /var/log/supervisor/grid-trading.err.log')
        print("\n服务日志:")
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        ssh.close()

if __name__ == '__main__':
    check_api() 