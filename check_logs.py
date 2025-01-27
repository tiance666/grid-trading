import paramiko

def check_logs():
    # 创建SSH客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # 连接到服务器
        ssh.connect('47.113.144.26', username='root', password='Chc20090629')
        
        # 检查supervisor错误日志
        stdin, stdout, stderr = ssh.exec_command('cat /var/log/supervisor/grid-trading.err.log')
        print("Supervisor错误日志:")
        print(stdout.read().decode())
        
        # 检查supervisor输出日志
        stdin, stdout, stderr = ssh.exec_command('cat /var/log/supervisor/grid-trading.log')
        print("\nSupervisor输出日志:")
        print(stdout.read().decode())
        
        # 检查应用错误日志
        stdin, stdout, stderr = ssh.exec_command('cat /var/log/grid-trading.err.log')
        print("\n应用错误日志:")
        print(stdout.read().decode())
        
        # 检查应用输出日志
        stdin, stdout, stderr = ssh.exec_command('cat /var/log/grid-trading.out.log')
        print("\n应用输出日志:")
        print(stdout.read().decode())
        
        # 检查supervisor状态
        stdin, stdout, stderr = ssh.exec_command('supervisorctl status')
        print("\nSupervisor状态:")
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        ssh.close()

if __name__ == '__main__':
    check_logs() 