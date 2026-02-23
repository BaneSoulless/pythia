import subprocess
import sys
import platform

def install_build_tools():
    system = platform.system().lower()
    if system == "windows":
        print("Installing Visual Studio Build Tools for Windows...")
        # This is tricky, as VS Build Tools require manual install, but we can try choco or something
        try:
            subprocess.check_call(["powershell", "-Command", "choco install visualcpp-build-tools -y"])
        except subprocess.CalledProcessError:
            print("Chocolatey not found or failed. Please install Visual Studio Build Tools manually.")
    elif system == "linux":
        print("Installing build-essential for Linux...")
        subprocess.check_call(["sudo", "apt-get", "update"])
        subprocess.check_call(["sudo", "apt-get", "install", "-y", "build-essential"])
    elif system == "darwin":  # macOS
        print("Installing Xcode Command Line Tools for macOS...")
        subprocess.check_call(["xcode-select", "--install"])
    else:
        print(f"Unsupported OS: {system}. Please install C++ build tools manually.")

def install_dependencies():
    print("Installing unified dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_lock.txt"])

if __name__ == "__main__":
    install_build_tools()
    install_dependencies()
    print("Environment setup complete.")