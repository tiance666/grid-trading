import paramiko

def run_remote_command():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect('47.113.144.26', username='root', password='Chc20090629')
        
        # 检查supervisor状态
        stdin, stdout, stderr = ssh.exec_command('supervisorctl status')
        print("Supervisor状态:")
        print(stdout.read().decode())
        
        # 重启grid-trading服务
        stdin, stdout, stderr = ssh.exec_command('supervisorctl restart grid-trading')
        print("\n重启服务:")
        print(stdout.read().decode())
        
        # 检查日志
        stdin, stdout, stderr = ssh.exec_command('tail -n 20 /var/log/supervisor/grid-trading.log')
        print("\n最新日志:")
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        ssh.close()

if __name__ == '__main__':
    run_remote_command() 