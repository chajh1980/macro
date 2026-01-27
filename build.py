#!/usr/bin/env python3
"""
Production build script for AutoMacro.
Optimized for distribution without debug output.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def get_build_type():
    """Determine build type from command line args."""
    if "--windowed" in sys.argv:
        return "windowed"
    else:
        return "console"

def build():
    """Build the application for distribution."""
    build_type = get_build_type()
    
    print(f"Starting {build_type} build...")
    
    # Clean previous build
    if Path("dist").exists():
        shutil.rmtree("dist")
        print("Cleaned previous build directory")
    
    # PyInstaller command for production build
    if build_type == "windowed":
        cmd = [
            "pyinstaller",
            "--name=AutoMacro",
            "--windowed",
            "--noconfirm",
            "--add-data=assets:assets",
            "--icon=assets/icon.icns" if Path("assets/icon.icns").exists() else None,
            "main.py"
        ]
    else:  # console
        cmd = [
            "pyinstaller",
            "--name=AutoMacro",
            "--console",
            "--noconfirm",
            "--add-data=assets:assets",
            "main.py"
        ]
    
    # Run build
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Build completed successfully!")
        
        # List created files
        if Path("dist").exists():
            print("\nCreated files:")
            for file in Path("dist").rglob("*"):
                size = file.stat().st_size
                print(f"  {file.name} ({size:,} bytes)")
    else:
        print(f"Build failed with return code: {result.returncode}")
        print("Error output:")
        print(result.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build()