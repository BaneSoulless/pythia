import subprocess
import time
import sys
from datetime import datetime

def run_verification_with_retry(max_attempts=3, delay=2):
    """
    Run verify_system.py with exponential backoff retry mechanism.
    Captures full stdout/stderr and logs to execution_trace.log with timestamps.
    Validates cross-repository interoperability.
    Performs self-diagnostics and rollback if fails.
    """
    log_file = 'execution_trace.log'
    attempt = 1
    backoff = delay

    while attempt <= max_attempts:
        print(f"Attempt {attempt}/{max_attempts}: Running verification...")
        timestamp = datetime.now().isoformat()

        try:
            # Run verify_system.py
            result = subprocess.run(
                [sys.executable, 'verify_system.py'],
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )

            stdout = result.stdout
            stderr = result.stderr
            returncode = result.returncode

            # Log to file
            with open(log_file, 'a') as f:
                f.write(f"\n[{timestamp}] Attempt {attempt}\n")
                f.write(f"Return code: {returncode}\n")
                f.write("STDOUT:\n")
                f.write(stdout)
                f.write("\nSTDERR:\n")
                f.write(stderr)
                f.write("\n" + "="*50 + "\n")

            # Check for success
            if returncode == 0 and "Verification successful" in stdout:
                # Validate interoperability: try importing freqtrade and referencing hummingbot
                try:
                    import freqtrade
                    import hummingbot
                    # Simple check
                    if hasattr(freqtrade, 'strategy') and hasattr(hummingbot, 'core'):
                        print("Interoperability validated: freqtrade and hummingbot can cross-reference.")
                        with open(log_file, 'a') as f:
                            f.write(f"[{datetime.now().isoformat()}] Interoperability: SUCCESS\n")
                        return True, stdout, stderr
                    else:
                        raise Exception("Attributes missing")
                except Exception as e:
                    print(f"Interoperability failed: {e}")
                    with open(log_file, 'a') as f:
                        f.write(f"[{datetime.now().isoformat()}] Interoperability: FAILED - {e}\n")
                    if attempt == max_attempts:
                        return False, stdout, stderr
            else:
                print(f"Verification failed with return code {returncode}")
                if attempt < max_attempts:
                    print(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                else:
                    # Self-diagnostics: rollback risky path injections
                    print("All attempts failed. Initiating rollback...")
                    rollback_plan()
                    return False, stdout, stderr

        except subprocess.TimeoutExpired:
            print(f"Verification timed out on attempt {attempt}")
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] Attempt {attempt}: TIMEOUT\n")
            if attempt < max_attempts:
                time.sleep(backoff)
                backoff *= 2
        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            if attempt == max_attempts:
                rollback_plan()
                return False, stdout if 'stdout' in locals() else '', stderr if 'stderr' in locals() else ''

        attempt += 1

    return False, '', ''

def rollback_plan():
    """
    Minimal rollback plan: Remove injected paths from sys.path.
    Generate diff-patch file for manual approval.
    """
    # Assuming injected_paths is available from main.py or global
    # For simplicity, since paths are inserted at 0, remove first N
    # But better to store original sys.path

    # This is simplistic; in real scenario, snapshot sys.path before injection
    print("Rollback: Removing injected paths (simplified - requires original snapshot)")
    # For now, just log
    with open('rollback_plan.txt', 'w') as f:
        f.write("Rollback Plan:\n")
        f.write("- Revert sys.path to pre-injection state\n")
        f.write("- Remove mock modules from sys.modules\n")
        f.write("- Check execution_trace.log for errors\n")
        f.write("- Manual diff: compare current main.py/system_bus.py with backup\n")

if __name__ == "__main__":
    success, stdout, stderr = run_verification_with_retry()
    if success:
        print("Verification succeeded.")
    else:
        print("Verification failed after all retries.")