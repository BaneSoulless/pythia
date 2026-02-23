import subprocess
import sys

def nuclear_fix():
    print(">>> ☢️ INITIATING NUCLEAR DEPENDENCY FIX ☢️ <<<")
    
    # 1. Aggressive Uninstall (Force purge V2)
    pkgs = ["pydantic", "pydantic-core", "fastapi", "email-validator"]
    print(f"    [PURGE] Uninstalling: {', '.join(pkgs)}")
    try:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y"] + pkgs, check=True)
    except subprocess.CalledProcessError as e:
        print(f"    [WARNING] Uninstall issue (might be already gone): {e}")
    
    # 2. Legacy Stack Install (Pin exact versions)
    # Pydantic 1.10.x is the last V1 release. FastAPI 0.95.2 supports it natively.
    legacy_stack = [
        "pydantic==1.10.13",
        "fastapi==0.95.2",
        "email-validator==2.1.0.post1",
        "uvicorn==0.23.2"
    ]
    print(f"    [INSTALL] Locking Legacy Stack: {', '.join(legacy_stack)}")
    subprocess.run([sys.executable, "-m", "pip", "install"] + legacy_stack, check=True)
    
    print(">>> ✅ DEPENDENCY GRAPH RE-ALIGNED TO LEGACY STANDARDS <<<")

if __name__ == "__main__":
    nuclear_fix()
