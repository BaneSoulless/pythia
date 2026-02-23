
import psutil
import os
import signal

def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                print(f"killing child {child.pid}")
                child.send_signal(signal.SIGTERM)
            except psutil.NoSuchProcess:
                pass
        print(f"killing parent {parent.pid}")
        parent.send_signal(signal.SIGTERM)
    except psutil.NoSuchProcess:
        pass

def kill_listening_ports(ports):
    print(f"Scanning for processes on ports: {ports}")
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port in ports:
                    print(f"Found {proc.name()} (PID {proc.pid}) on port {conn.laddr.port}. TERMINATING.")
                    kill_process_tree(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def kill_zombies_by_name(names):
    print(f"Scanning for zombie processes: {names}")
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid == current_pid:
                continue
            
            # Simple check by name
            if proc.name() in names:
                # Optional: Refine by cwd to avoid killing system processes
                # But for 'node.exe' in this context it's safer to kill if unsure, or checking cwd
                try:
                    p_cwd = proc.cwd()
                    if "AI-Trading-Bot" in p_cwd:
                         print(f"Found Zombie {proc.name()} (PID {proc.pid}) in {p_cwd}. TERMINATING.")
                         proc.kill()
                except:
                    pass
        except:
            pass

if __name__ == "__main__":
    print(">>> 🟢 EMERGENCY KILL SWITCH ACTIVATED")
    
    # 1. Kill Ports
    kill_listening_ports([8000, 5173, 5555, 5556, 5557])
    
    # 2. Kill Python/Node zombies in this folder
    kill_zombies_by_name(["python.exe", "node.exe"])
    
    print(">>> 💀 ZOMBIES CLEARED. PORTS FREED.")
