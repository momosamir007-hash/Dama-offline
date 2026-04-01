# ui/camera.py
"""
إدارة الكاميرا والتقاط الصور
يدعم:
  - الكاميرا المباشرة (webcam)
  - كاميرا الهاتف (عبر IP)
  - ملفات الصور
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Callable
from enum import Enum
from pathlib import Path
import time
import os

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


# ──────────────────────────────────────────────
# التعدادات والإعدادات
# ──────────────────────────────────────────────

class CaptureMode(Enum):
    """أوضاع الالتقاط"""
    WEBCAM = "webcam"               # كاميرا الكمبيوتر
    IP_CAMERA = "ip_camera"         # كاميرا عبر IP (هاتف)
    FILE = "file"                   # ملف صورة
    SCREENSHOT = "screenshot"       # لقطة شاشة


@dataclass
class CameraConfig:
    """إعدادات الكاميرا"""
    device_id: int = 0                     # رقم الكاميرا
    ip_address: str = ""                   # عنوان IP
    resolution: Tuple[int, int] = (1280, 720)
    fps: int = 30
    auto_focus: bool = True
    brightness: float = 1.0
    contrast: float = 1.0
    
    # مجلد حفظ الصور
    save_dir: str = "captures"
    
    # إعدادات العرض
    show_guides: bool = True               # خطوط إرشادية
    show_fps: bool = True
    window_name: str = "Domino Camera"


@dataclass
class CaptureResult:
    """نتيجة الالتقاط"""
    image: Optional[object] = None         # np.ndarray
    timestamp: float = 0.0
    filepath: Optional[str] = None
    mode: CaptureMode = CaptureMode.WEBCAM
    success: bool = False
    error: str = ""


# ──────────────────────────────────────────────
# مدير الكاميرا
# ──────────────────────────────────────────────

class CameraManager:
    """
    مدير الكاميرا الرئيسي
    
    يوفر واجهة موحدة لالتقاط الصور من مصادر مختلفة
    مع أدوات مساعدة (خطوط إرشادية، حفظ، معاينة)
    """
    
    def __init__(self, config: CameraConfig = None):
        self.config = config or CameraConfig()
        self._cap = None             # cv2.VideoCapture
        self._is_open = False
        self._frame_count = 0
        self._fps_actual = 0.0
        self._last_frame_time = 0.0
        
        # التأكد من وجود مجلد الحفظ
        os.makedirs(self.config.save_dir, exist_ok=True)
        
        if not CV2_AVAILABLE:
            print(
                "⚠️ مكتبة OpenCV غير مثبتة!\n"
                "   ثبّتها بـ: pip install opencv-python"
            )
    
    # ──────────────────────────────────────────
    # فتح وإغلاق الكاميرا
    # ──────────────────────────────────────────
    
    def open(
        self, 
        mode: CaptureMode = CaptureMode.WEBCAM
    ) -> bool:
        """فتح مصدر الفيديو"""
        if not CV2_AVAILABLE:
            return False
        
        try:
            if mode == CaptureMode.WEBCAM:
                self._cap = cv2.VideoCapture(
                    self.config.device_id
                )
            elif mode == CaptureMode.IP_CAMERA:
                url = self.config.ip_address
                if not url:
                    print("❌ عنوان IP غير محدد")
                    return False
                self._cap = cv2.VideoCapture(url)
            else:
                return False
            
            if not self._cap.isOpened():
                print("❌ تعذر فتح الكاميرا")
                return False
            
            # ضبط الإعدادات
            w, h = self.config.resolution
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            self._cap.set(
                cv2.CAP_PROP_FPS, self.config.fps
            )
            
            if self.config.auto_focus:
                self._cap.set(
                    cv2.CAP_PROP_AUTOFOCUS, 1
                )
            
            self._is_open = True
            print(
                f"✅ الكاميرا مفتوحة "
                f"({w}x{h} @ {self.config.fps}fps)"
            )
            return True
            
        except Exception as e:
            print(f"❌ خطأ في فتح الكاميرا: {e}")
            return False
    
    def close(self):
        """إغلاق الكاميرا"""
        if self._cap and self._cap.isOpened():
            self._cap.release()
        
        if CV2_AVAILABLE:
            cv2.destroyAllWindows()
        
        self._is_open = False
        print("📷 تم إغلاق الكاميرا")
    
    @property
    def is_open(self) -> bool:
        return (
            self._is_open and 
            self._cap is not None and 
            self._cap.isOpened()
        )
    
    # ──────────────────────────────────────────
    # قراءة الإطارات
    # ──────────────────────────────────────────
    
    def read_frame(self) -> Optional[object]:
        """قراءة إطار واحد"""
        if not self.is_open:
            return None
        
        ret, frame = self._cap.read()
        if not ret:
            return None
        
        # حساب FPS الفعلي
        current_time = time.time()
        if self._last_frame_time > 0:
            dt = current_time - self._last_frame_time
            if dt > 0:
                self._fps_actual = 1.0 / dt
        self._last_frame_time = current_time
        self._frame_count += 1
        
        # تعديل السطوع والتباين
        if (
            self.config.brightness != 1.0 or 
            self.config.contrast != 1.0
        ):
            frame = cv2.convertScaleAbs(
                frame,
                alpha=self.config.contrast,
                beta=(self.config.brightness - 1.0) * 50
            )
        
        return frame
    
    # ──────────────────────────────────────────
    # الالتقاط التفاعلي
    # ──────────────────────────────────────────
    
    def capture_interactive(self) -> CaptureResult:
        """
        التقاط تفاعلي مع معاينة مباشرة
        
        المفاتيح:
          SPACE  = التقاط
          G      = تبديل الخطوط الإرشادية
          +/-    = السطوع
          Q/ESC  = إلغاء
        """
        if not CV2_AVAILABLE:
            return CaptureResult(
                success=False,
                error="OpenCV غير مثبت"
            )
        
        if not self.is_open:
            if not self.open():
                return CaptureResult(
                    success=False,
                    error="تعذر فتح الكاميرا"
                )
        
        result = CaptureResult(mode=CaptureMode.WEBCAM)
        show_guides = self.config.show_guides
        
        print("\n📷 المعاينة المباشرة:")
        print("  SPACE = التقاط | G = خطوط إرشادية")
        print("  +/- = سطوع | Q = إلغاء")
        
        while True:
            frame = self.read_frame()
            if frame is None:
                continue
            
            # إعداد إطار العرض
            display = frame.copy()
            
            # الخطوط الإرشادية
            if show_guides:
                display = self._draw_guides(display)
            
            # معلومات على الشاشة
            display = self._draw_info_overlay(display)
            
            # عرض
            cv2.imshow(
                self.config.window_name, display
            )
            
            # معالجة المفاتيح
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord(' '):
                # التقاط!
                result.image = frame.copy()
                result.timestamp = time.time()
                result.success = True
                
                # حفظ تلقائي
                result.filepath = self._save_capture(frame)
                
                # ومضة بيضاء (تأثير التصوير)
                self._flash_effect()
                
                print(f"  ✅ تم الالتقاط!")
                if result.filepath:
                    print(f"  💾 حُفظت: {result.filepath}")
                break
            
            elif key == ord('g') or key == ord('G'):
                show_guides = not show_guides
            
            elif key == ord('+') or key == ord('='):
                self.config.brightness = min(
                    2.0, 
                    self.config.brightness + 0.1
                )
            
            elif key == ord('-'):
                self.config.brightness = max(
                    0.2, 
                    self.config.brightness - 0.1
                )
            
            elif key == ord('q') or key == 27:  # ESC
                result.error = "ألغى المستخدم"
                break
        
        cv2.destroyWindow(self.config.window_name)
        return result
    
    def capture_auto(
        self,
        delay: float = 3.0,
        num_frames: int = 5
    ) -> CaptureResult:
        """
        التقاط تلقائي بعد عد تنازلي
        يأخذ عدة صور ويختار الأوضح
        """
        if not CV2_AVAILABLE:
            return CaptureResult(
                success=False,
                error="OpenCV غير مثبت"
            )
        
        if not self.is_open:
            if not self.open():
                return CaptureResult(
                    success=False,
                    error="تعذر فتح الكاميرا"
                )
        
        # عد تنازلي
        start = time.time()
        while time.time() - start < delay:
            frame = self.read_frame()
            if frame is None:
                continue
            
            remaining = delay - (time.time() - start)
            display = frame.copy()
            
            # عرض العد التنازلي
            text = f"التقاط خلال {remaining:.1f}s"
            cv2.putText(
                display, text,
                (50, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                2.0, (0, 0, 255), 3
            )
            
            cv2.imshow(
                self.config.window_name, display
            )
            cv2.waitKey(1)
        
        # التقاط عدة صور واختيار الأوضح
        frames = []
        for _ in range(num_frames):
            frame = self.read_frame()
            if frame is not None:
                sharpness = self._measure_sharpness(frame)
                frames.append((frame, sharpness))
            time.sleep(0.1)
        
        cv2.destroyWindow(self.config.window_name)
        
        if not frames:
            return CaptureResult(
                success=False,
                error="لم يتم التقاط أي إطار"
            )
        
        # اختيار الأوضح
        best_frame, best_sharpness = max(
            frames, key=lambda x: x[1]
        )
        
        filepath = self._save_capture(best_frame)
        
        return CaptureResult(
            image=best_frame,
            timestamp=time.time(),
            filepath=filepath,
            success=True
        )
    
    # ──────────────────────────────────────────
    # التقاط من ملف
    # ──────────────────────────────────────────
    
    @staticmethod
    def capture_from_file(
        filepath: str
    ) -> CaptureResult:
        """التقاط من ملف صورة"""
        if not CV2_AVAILABLE:
            return CaptureResult(
                success=False,
                error="OpenCV غير مثبت"
            )
        
        path = Path(filepath)
        
        if not path.exists():
            return CaptureResult(
                success=False,
                error=f"الملف غير موجود: {filepath}"
            )
        
        supported = {
            '.jpg', '.jpeg', '.png', 
            '.bmp', '.tiff', '.webp'
        }
        
        if path.suffix.lower() not in supported:
            return CaptureResult(
                success=False,
                error=(
                    f"صيغة غير مدعومة: {path.suffix}. "
                    f"المدعوم: {supported}"
                )
            )
        
        image = cv2.imread(str(path))
        
        if image is None:
            return CaptureResult(
                success=False,
                error=f"تعذرت قراءة الصورة: {filepath}"
            )
        
        print(
            f"✅ تم تحميل الصورة: "
            f"{image.shape[1]}x{image.shape[0]}"
        )
        
        return CaptureResult(
            image=image,
            timestamp=time.time(),
            filepath=str(path),
            mode=CaptureMode.FILE,
            success=True
        )
    
    # ──────────────────────────────────────────
    # التقاط من هاتف (IP Camera)
    # ──────────────────────────────────────────
    
    def setup_phone_camera(self) -> str:
        """
        إعداد كاميرا الهاتف
        
        يدعم تطبيقات:
        - IP Webcam (Android)
        - DroidCam
        - EpocCam (iOS)
        """
        print("\n📱 إعداد كاميرا الهاتف:")
        print("=" * 40)
        print(
            "1. ثبّت تطبيق 'IP Webcam' "
            "على هاتفك (Android)"
        )
        print("   أو 'DroidCam' (Android/iOS)")
        print(
            "2. افتح التطبيق واضغط "
            "'Start Server'"
        )
        print("3. ستظهر لك عنوان IP مثل:")
        print("   http://192.168.1.100:8080")
        print("=" * 40)
        
        ip = input(
            "\nأدخل عنوان IP الكامل "
            "(أو اضغط Enter للإلغاء): "
        ).strip()
        
        if not ip:
            return ""
        
        # تنسيق العنوان
        if not ip.startswith('http'):
            ip = f"http://{ip}"
        
        # إضافة مسار الفيديو
        if '/video' not in ip:
            if ip.endswith('/'):
                ip += 'video'
            else:
                ip += '/video'
        
        self.config.ip_address = ip
        print(f"📡 عنوان الكاميرا: {ip}")
        
        return ip
    
    # ──────────────────────────────────────────
    # أدوات الرسم على الإطار
    # ──────────────────────────────────────────
    
    def _draw_guides(self, frame) -> object:
        """رسم خطوط إرشادية"""
        if not CV2_AVAILABLE:
            return frame
        
        h, w = frame.shape[:2]
        color = (0, 255, 0)  # أخضر
        thickness = 1
        
        # خطوط الثلث (Rule of thirds)
        for i in range(1, 3):
            # أفقية
            y = h * i // 3
            cv2.line(
                frame, (0, y), (w, y), 
                color, thickness
            )
            # عمودية
            x = w * i // 3
            cv2.line(
                frame, (x, 0), (x, h), 
                color, thickness
            )
        
        # مستطيل مركزي (منطقة الاهتمام)
        margin_x = w // 6
        margin_y = h // 6
        cv2.rectangle(
            frame,
            (margin_x, margin_y),
            (w - margin_x, h - margin_y),
            (0, 200, 255),  # برتقالي
            2
        )
        
        # نص إرشادي
        cv2.putText(
            frame,
            "Place dominoes in the orange box",
            (margin_x, margin_y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (0, 200, 255), 1
        )
        
        return frame
    
    def _draw_info_overlay(self, frame) -> object:
        """رسم معلومات على الإطار"""
        if not CV2_AVAILABLE:
            return frame
        
        h, w = frame.shape[:2]
        
        # خلفية شبه شفافة للنص
        overlay = frame.copy()
        cv2.rectangle(
            overlay, (0, 0), (250, 80), 
            (0, 0, 0), -1
        )
        frame = cv2.addWeighted(
            overlay, 0.5, frame, 0.5, 0
        )
        
        # FPS
        if self.config.show_fps:
            fps_text = f"FPS: {self._fps_actual:.0f}"
            cv2.putText(
                frame, fps_text,
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (0, 255, 0), 1
            )
        
        # السطوع
        bright_text = (
            f"Brightness: "
            f"{self.config.brightness:.1f}"
        )
        cv2.putText(
            frame, bright_text,
            (10, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (255, 255, 255), 1
        )
        
        # عدد الإطارات
        cv2.putText(
            frame, f"Frame: {self._frame_count}",
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4, (200, 200, 200), 1
        )
        
        # تعليمات
        help_text = "SPACE:Capture | G:Guides | Q:Quit"
        cv2.putText(
            frame, help_text,
            (10, h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (200, 200, 200), 1
        )
        
        return frame
    
    def _flash_effect(self):
        """تأثير ومضة عند التصوير"""
        if not CV2_AVAILABLE or not self.is_open:
            return
        
        frame = self.read_frame()
        if frame is not None:
            white = np.ones_like(frame) * 255
            cv2.imshow(self.config.window_name, white)
            cv2.waitKey(100)
            cv2.imshow(self.config.window_name, frame)
            cv2.waitKey(100)
    
    # ──────────────────────────────────────────
    # أدوات مساعدة
    # ──────────────────────────────────────────
    
    def _save_capture(self, frame) -> Optional[str]:
        """حفظ الصورة الملتقطة"""
        if not CV2_AVAILABLE:
            return None
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"domino_capture_{timestamp}.jpg"
        filepath = os.path.join(
            self.config.save_dir, filename
        )
        
        # ضغط JPEG بجودة عالية
        params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        cv2.imwrite(filepath, frame, params)
        
        return filepath
    
    @staticmethod
    def _measure_sharpness(frame) -> float:
        """
        قياس وضوح الصورة
        باستخدام Laplacian variance
        قيمة أعلى = صورة أوضح
        """
        if not CV2_AVAILABLE:
            return 0.0
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()
    
    @staticmethod
    def list_cameras() -> List[int]:
        """
        عرض الكاميرات المتاحة
        """
        if not CV2_AVAILABLE:
            return []
        
        available = []
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                ret, _ = cap.read()
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(
                    f"  📷 كاميرا {i}: "
                    f"{w}x{h} "
                    f"({'✅' if ret else '❌'})"
                )
                cap.release()
        
        if not available:
            print("  ❌ لم يتم العثور على كاميرات")
        
        return available
    
    def __enter__(self):
        """دعم context manager"""
        self.open()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def __del__(self):
        self.close()
