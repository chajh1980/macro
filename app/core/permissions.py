import sys
import os
import subprocess
import time
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

def check_accessibility_permission():
    """
    Check if the application has accessibility permission.
    Returns True if granted, False otherwise.
    """
    if sys.platform != "darwin":
        return True

    # Use a simple check: try to create a key event source
    # This usually returns None if no permission
    # However, a more reliable way without extra deps is checking if we can control mouse
    # But that might cause side effects.
    
    # Alternative: Check via tccutil or similar? No, tccutil is for resetting.
    # Best way in pure python without pyobjc is tricky.
    # We can try to use AppleScript to check "System Events" but that itself needs permission.
    
    # Let's try the "trusted" check via AXIsProcessTrusted
    try:
        import ctypes
        # Load ApplicationServices framework
        # /System/Library/Frameworks/ApplicationServices.framework/ApplicationServices
        lib = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        # Boolean AXIsProcessTrusted(void)
        is_trusted = lib.AXIsProcessTrusted()
        return bool(is_trusted)
    except Exception as e:
        print(f"Permission check error: {e}")
        return False

def request_accessibility_permission():
    """
    Request accessibility permission by opening the prompt options.
    """
    if sys.platform != "darwin":
        return

    # AXIsProcessTrustedWithOptions can trigger the prompt
    try:
        import ctypes
        lib = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        # Boolean AXIsProcessTrustedWithOptions(CFDictionaryRef options)
        # We need to pass kAXTrustedCheckOptionPrompt = true
        
        # Since constructing CFDictionary in ctypes is hard, let's use a simpler trick:
        # Just tell the user to open it.
        # Or use AppleScript to open the prefs pane.
        pass
    except:
        pass
    
    # Open System Settings
    open_system_settings("Privacy_Accessibility")

def check_screen_recording_permission():
    """
    Check screen recording permission by actually trying to capture screen.
    Returns True if screenshot works, False otherwise.
    """
    if sys.platform != "darwin":
        return True

    # Test by actually taking a screenshot
    try:
        import pyautogui
        # Take a small 1x1 screenshot to test permission
        # This should be fast and minimally invasive
        test_ss = pyautogui.screenshot(region=(0, 0, 1, 1))

        # Check if we got valid image data (not all black/transparent)
        import numpy as np
        img_np = np.array(test_ss)

        # On macOS without permission, screenshot is typically 1x1 black image
        # or returns data that's all zeros
        if img_np.size > 0 and not np.all(img_np == 0):
            # We got actual screenshot data, permission likely granted
            return True
        else:
            # All black or empty, permission likely denied
            print("Screen capture test failed: got black/empty image")
            return False

    except pyautogui.ImageNotFoundException:
        # Screenshot failed completely
        print("Screen capture failed: ImageNotFoundException")
        return False
    except Exception as e:
        # Other error during screenshot
        print(f"Screen capture test failed with exception: {e}")
        return False

def open_system_settings(pane_id):
    """
    Open macOS System Settings to a specific pane.
    """
    # macOS Ventura+ uses x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility
    # Older uses different scheme.
    
    # Try generic URL scheme
    url = QUrl("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
    QDesktopServices.openUrl(url)

def ensure_permissions(parent=None):
    """
    Check and guide user for permissions.
    Returns True if all permissions granted, False otherwise.
    """
    if sys.platform != "darwin":
        return True

    # Check accessibility permission
    if not check_accessibility_permission():
        msg = QMessageBox(parent)
        msg.setWindowTitle("권한 필요")
        msg.setText("매크로 실행을 위해 '손쉬운 사용' 권한이 필요합니다.")
        msg.setInformativeText("시스템 설정 > 개인정보 보호 및 보안 > 손쉬운 사용\n에서 터미널(또는 Python)을 허용해 주세요.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.button(QMessageBox.StandardButton.Ok).setText("설정 열기")

        ret = msg.exec()
        if ret == QMessageBox.StandardButton.Ok:
            # Open settings
            subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])

        return False

    # Check screen recording permission
    if not check_screen_recording_permission():
        msg = QMessageBox(parent)
        msg.setWindowTitle("화면 기록 권한 필요")
        msg.setText("스크린샷 캡처를 위해 '화면 기록' 권한이 필요합니다.")
        msg.setInformativeText("화면 기록 권한이 없으면 이미지 인식이 작동하지 않습니다.\n\n시스템 설정 > 개인정보 보호 및 보안 > 화면 기록\n에서 이 앱을 허용해 주세요.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.button(QMessageBox.StandardButton.Ok).setText("설정 열기")

        ret = msg.exec()
        if ret == QMessageBox.StandardButton.Ok:
            # Open settings for screen recording
            subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenRecording"])

        return False

    return True

    if not check_accessibility_permission():
        msg = QMessageBox(parent)
        msg.setWindowTitle("권한 필요")
        msg.setText("매크로 실행을 위해 '손쉬운 사용' 권한이 필요합니다.")
        msg.setInformativeText("시스템 설정 > 개인정보 보호 및 보안 > 손쉬운 사용\n에서 터미널(또는 Python)을 허용해 주세요.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.button(QMessageBox.StandardButton.Ok).setText("설정 열기")
        
        ret = msg.exec()
        if ret == QMessageBox.StandardButton.Ok:
            # Trigger prompt via ctypes if possible to register the app in the list
            try:
                import ctypes
                lib = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
                # kAXTrustedCheckOptionPrompt
                # We can't easily pass the dict, but calling AXIsProcessTrusted might not trigger it if already denied.
                # Let's just open the settings.
                pass
            except:
                pass
            
            # Open settings
            # For Ventura+:
            subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
            
        return False
        
    return True
