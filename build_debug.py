#!/usr/bin/env python3
"""
Debug build script for AutoMacro.
Includes console output and debugging features.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build():
    """Build the application for debugging."""
    print("Starting debug build...")
    
    # Clean previous build
    if Path("dist").exists():
        shutil.rmtree("dist")
        print("Cleaned previous build directory")
    
    # PyInstaller command for debug build
    cmd = [
        "pyinstaller",
        "--name=AutoMacro-Debug",
        "--console",
        "--noconfirm",
        "--add-data=assets:assets",
        "--icon=assets/icon.icns" if Path("assets/icon.icns").exists() else None,
        "main.py"
    ]
    
    # Run build
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Debug build completed successfully!")
        
        # List created files
        if Path("dist").exists():
            print("\nCreated files:")
            for file in Path("dist").rglob("*"):
                size = file.stat().st_size
                print(f"  {file.name} ({size:,} bytes)")
    else:
        print(f"Debug build failed with return code: {result.returncode}")
        print("Error output:")
        print(result.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build()