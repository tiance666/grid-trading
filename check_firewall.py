import paramiko

def check_firewall():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect('47.113.144.26', username='root', password='Chc20090629')
        
        # 检查防火墙状态
        stdin, stdout, stderr = ssh.exec_command('ufw status')
        print("防火墙状态:")
        print(stdout.read().decode())
        
        # 检查8000端口
        stdin, stdout, stderr = ssh.exec_command('netstat -tlnp | grep 8000')
        print("\n8000端口状态:")
        print(stdout.read().decode())
        
        # 开放8000端口
        stdin, stdout, stderr = ssh.exec_command('ufw allow 8000/tcp')
        print("\n开放8000端口:")
        print(stdout.read().decode())
        
        # 重启uvicorn服务
        stdin, stdout, stderr = ssh.exec_command('cd /home/trading/grid-trading && python3 -m uvicorn src.server.app:app --host 0.0.0.0 --port 8000 &')
        print("\n重启uvicorn服务:")
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        ssh.close()

if __name__ == '__main__':
    check_firewall() 