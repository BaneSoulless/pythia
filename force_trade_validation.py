import json
import time
import subprocess
import sys
import pandas as pd
import sqlite3
import os
import signal
CONFIG_PATH = 'config.json'
DB_PATH = 'backend/app.db'
LAUNCHER_SCRIPT = 'nexus_launcher.py'

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=4)

def check_ledger():
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query('SELECT * FROM trades', conn)
        conn.close()
        if not df.empty:
            print(f'\n✅ KINETIC VERIFICATION SUCCESS! Found {len(df)} Trades.')
            print(df.tail(1).to_string())
            return True
    except Exception:
        pass
    return False

def main():
    print('🚀 INITIATING KINETIC VALIDATION PROTOCOL...')
    original_config = load_config()
    print('Locked Original Config.')
    aggressive_config = original_config.copy()
    aggressive_config['strategy']['rsi_buy'] = 99
    aggressive_config['strategy']['rsi_sell'] = 1
    save_config(aggressive_config)
    print('💉 INJECTED AGGRESSIVE PARAMETERS (RSI 99/1)')
    print('☠️  Clearing process table (preserving self)...')
    current_pid = os.getpid()
    os.system(f'taskkill /F /IM python.exe /FI "PID ne {current_pid}" >nul 2>&1')
    time.sleep(2)
    print('🔥 IGNITING CORE...')
    proc = subprocess.Popen([sys.executable, LAUNCHER_SCRIPT], creationflags=subprocess.CREATE_NEW_CONSOLE)
    print('👀 WATCHDOG ACTIVE: Polling Ledger...')
    start_time = time.time()
    trade_confirmed = False
    while time.time() - start_time < 60:
        if check_ledger():
            trade_confirmed = True
            break
        time.sleep(2)
        print('.', end='', flush=True)
    print('\n🛑 STOPPING SYSTEM...')
    os.system('taskkill /F /IM python.exe /T >nul 2>&1')
    save_config(original_config)
    print('♻️ CONFIGURATION RESTORED.')
    if trade_confirmed:
        print('🏆 MISSION COMPLETE: END-TO-END PERSISTENCE VERIFIED.')
        sys.exit(0)
    else:
        print('❌ MISSION FAILED: TIMEOUT (No trades generated). Check Strategy Logic.')
        sys.exit(1)
if __name__ == '__main__':
    main()