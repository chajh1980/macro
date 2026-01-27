"""
Constants for AutoMacro application.
Centralized configuration values to improve maintainability.
"""

# Template cache configuration
TEMPLATE_CACHE_SIZE = 100
MAX_VISITED_MATCHES = 1000

# Default values for step conditions and actions
DEFAULT_CONFIDENCE = 0.8
DEFAULT_DEDUPLICATE_RADIUS = 10
DEFAULT_SCAN_INTERVAL_MS = 500
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_STEP_INTERVAL_MS = 5

# Window size percentages
WINDOW_SMALL_PCT = 0.3  # 30%
WINDOW_MEDIUM_PCT = 0.5  # 50%
WINDOW_LARGE_PCT = 0.6  # 60%

# Memory management
MAX_VISITED_MATCHES_BEFORE_CLEANUP = 1000

# Build configuration
BUILD_WINDOWED = False  # Default: windowed mode for debugging
BUILD_CONSOLE = False     # Default: production build

# Update check intervals (hours)
UPDATE_CHECK_INTERVAL_HOURS = 24

# Permission check messages
PERMISSION_ACCESSIBILITY_MSG = """
매크로 실행을 위해 '손쉬운 사용' 권한이 필요합니다.
시스템 설정 > 개인정보 보호 및 보안 > 손쉬운 사용\n에서 터미널(또는 Python)을 허용해 주세요.
"""
PERMISSION_SCREEN_RECORDING_MSG = """
스크린샷 캡처를 위해 '화면 기록' 권한이 필요합니다.
화면 기록 권한이 없으면 이미지 인식이 작동하지 않습니다.
시스템 설정 > 개인정보 보호 및 보안 > 화면 기록\n에서 이 앱을 허용해 주세요.
"""