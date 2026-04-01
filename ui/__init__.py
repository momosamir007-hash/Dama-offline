# ui/__init__.py
"""
واجهة المستخدم - العرض والإدخال والكاميرا
"""

from ui.display import GameDisplay, Colors
from ui.manual_input import ManualInput
from ui.camera import CameraManager, CaptureMode

__all__ = [
    'GameDisplay',
    'Colors',
    'ManualInput',
    'CameraManager',
    'CaptureMode',
]
