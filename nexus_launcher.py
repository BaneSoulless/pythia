import subprocess
import sys
import time
import os
import signal
import platform

# Configuration
# CRITICAL FIX: Point to the ROOT main.py, not the backend legacy folder
CORE_SCRIPT = "main.py" 
BRIDGE_SCRIPT = "interface_bridge.py"
FRONTEND_DIR = "frontend"

def kill_process_tree(pid):
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception:
        pass

def main():
    print(">>> 🌌 INITIATING NEXUS LAUNCH SEQUENCE (FINAL FIX) 🌌 <<<")

    # 1. CLEANUP (Kill Port 8000/5173/5555)
    print(">>> [PHASE 1] PORT SANITATION")
    subprocess.run([sys.executable, "kill_ports.py"])

    # 2. RUNTIME ENVIRONMENT CHECK
    env = os.environ.copy()
    # Check if local node exists and prepend to path
    local_node = os.path.join(os.getcwd(), ".runtime", "node")
    if os.path.exists(local_node):
        print(f"    [RUNTIME] Using Encapsulated Node.js at {local_node}")
        env["PATH"] = local_node + os.pathsep + env["PATH"]

    # 3. LAUNCH SUBSYSTEMS
    print(">>> [PHASE 3] ACTIVATING SUBSYSTEMS")
    
    # Bridge
    print(f"    Igniting Interface Bridge ({BRIDGE_SCRIPT})...")
    p_bridge = subprocess.Popen([sys.executable, BRIDGE_SCRIPT], cwd=os.getcwd())
    
    # Core (THE CORRECT ONE)
    print(f"    Igniting Cognitive Core ({CORE_SCRIPT})...")
    p_core = subprocess.Popen([sys.executable, CORE_SCRIPT], cwd=os.getcwd())
    
    # Frontend
    print("    Igniting React Frontend (Vite)...")
    # Use shell=True for npm to resolve correctly in some envs
    p_front = subprocess.Popen("npm run dev", cwd=FRONTEND_DIR, shell=True, env=env)

    print(f"    > Bridge PID: {p_bridge.pid}")
    print(f"    > Core PID: {p_core.pid}")
    print(f"    > Frontend PID: {p_front.pid}")

    # 4. MONITORING LOOP
    print(">>> [PHASE 4] SYSTEM MONITORING (Ctrl+C to Stop)...")
    print("----------------------------------------")
    print(">>> ✅ SYSTEM STATUS: GREEN")
    print(">>> DASHBOARD: http://localhost:5173")
    
    try:
        while True:
            time.sleep(2)
            if p_core.poll() is not None:
                print("!!! CORE DIED !!! Restarting...")
                p_core = subprocess.Popen([sys.executable, CORE_SCRIPT], cwd=os.getcwd())
            if p_bridge.poll() is not None:
                print("!!! BRIDGE DIED !!! Restarting...")
                p_bridge = subprocess.Popen([sys.executable, BRIDGE_SCRIPT], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("\n>>> SHUTDOWN SEQUENCE INITIATED...")
        kill_process_tree(p_bridge.pid)
        kill_process_tree(p_core.pid)
        kill_process_tree(p_front.pid)
        # Extra safety kill
        subprocess.run([sys.executable, "kill_ports.py"])
        print(">>> SYSTEM HALTED.")

if __name__ == "__main__":
    main()
