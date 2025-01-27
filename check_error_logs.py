import paramiko

def check_error_logs():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect('47.113.144.26', username='root', password='Chc20090629')
        
        # 检查错误日志
        stdin, stdout, stderr = ssh.exec_command('tail -n 50 /var/log/supervisor/grid-trading.err.log')
        print("错误日志:")
        print(stdout.read().decode())
        
        # 检查Python包
        stdin, stdout, stderr = ssh.exec_command('pip3 list | grep -E "fastapi|uvicorn|websockets|python-binance"')
        print("\nPython包:")
        print(stdout.read().decode())
        
        # 检查项目文件
        stdin, stdout, stderr = ssh.exec_command('ls -la /home/trading/grid-trading/src/server/')
        print("\n项目文件:")
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        ssh.close()

if __name__ == '__main__':
    check_error_logs() 