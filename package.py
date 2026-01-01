import os
import sys
import subprocess
import platform

def build():
    os_name = platform.system()
    print(f"Detected OS: {os_name}")
    
    # Common PyInstaller arguments
    args = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--name=AutoMacro", # Application Name
        # "--windowed", # ENABLE CONSOLE FOR DEBUGGING (Segfault)
        "--console",
        "--onefile", # Single file executable (start slower, cleaner).
        # "--onedir", # Directory based 
        
        # Main Entry Point
        "main.py",
        
        # Hidden imports if needed (PyQt6 often needs help?)
        # Generally PyInstaller finds them, but sometimes...
        "--hidden-import=app",
        "--hidden-import=app.core",
        "--hidden-import=app.ui",
        
        # Paths
        "--add-data=app:app", # Copy app package? No, it compiles it.
        # Assets handling?
        # If we have assets folder or workflows folder, we might need to copy them manually or include them.
        # Workflows are user data, stored in a specific dir. The app should handle creating it.
        # Assets like 'target_*.png' are inside workflow dirs.
    ]
    
    # OS Specifics
    if os_name == "Darwin": # macOS
        # args.append("--target-architecture=universal2") # universal2 is tricky with mixed wheels. Let's stick to native arch of the runner.
        pass
    elif os_name == "Windows":      
        # args.append("--icon=icon.ico") # If we had an icon
        pass

    print("Running PyInstaller...")
    print("Command:", " ".join(args))
    
    try:
        subprocess.check_call(args)
        print("\n" + "="*50)
        print("Build Successful!")
        print("="*50)
        
        if os_name == "Darwin":
            print("You can find the app in: dist/AutoMacro")
        elif os_name == "Windows":
            print("You can find the executable in: dist/AutoMacro.exe")
            
    except subprocess.CalledProcessError as e:
        print("Build Failed:", e)
        print("Make sure you have installed requirements: pip install -r requirements.txt")
        sys.exit(1) # CRITICAL: Exit with error code so CI knows it failed

if __name__ == "__main__":
    build()
