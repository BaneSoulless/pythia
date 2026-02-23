import psutil
import logging
import subprocess
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def kill_zombies(ports=[8000, 5173, 5555, 5556, 5557]):
    logging.info(f"💣 AGGRESSIVE SCAN ON PORTS: {ports}")
    killed = 0
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port in ports:
                    logging.warning(f"   >>> FORCE KILLING PID {proc.pid} ({proc.name()}) on Port {conn.laddr.port}")
                    try:
                        # Try psutil kill first
                        proc.kill()
                        # Backup: Taskkill for Windows
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], 
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except:
                        pass
                    killed += 1
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    if killed == 0:
        logging.info("✅ NO ZOMBIES DETECTED.")
    else:
        logging.info(f"💥 SANITATION COMPLETE. {killed} PROCESSES TERMINATED.")

if __name__ == "__main__":
    kill_zombies()