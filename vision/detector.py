# vision/detector.py
"""
المُكتشف الرئيسي - يجمع كل مكونات الرؤية
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

from game_engine.domino_board import DominoTile
from vision.preprocessor import ImagePreprocessor
from vision.pip_counter import PipCounter


@dataclass
class DetectionResult:
    """نتيجة اكتشاف حجر واحد"""
    tile: DominoTile
    confidence: float           # نسبة الثقة
    bounding_box: Tuple[int, int, int, int]  # x, y, w, h
    image_crop: Optional[np.ndarray] = None


class DominoDetector:
    """
    المُكتشف الرئيسي لأحجار الدومينو
    
    يدعم طريقتين:
    1. OpenCV التقليدية (بدون تدريب)
    2. YOLO (يحتاج نموذج مدرب)
    """
    
    def __init__(self, method: str = "opencv"):
        """
        method: "opencv" أو "yolo"
        """
        self.method = method
        self.preprocessor = ImagePreprocessor()
        self.pip_counter = PipCounter()
        
        if method == "yolo":
            self._load_yolo_model()
    
    def _load_yolo_model(self):
        """تحميل نموذج YOLO"""
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO("models/yolo_dominoes.pt")
        except Exception as e:
            print(f"⚠️ تعذر تحميل YOLO: {e}")
            print("سيتم استخدام OpenCV بدلاً")
            self.method = "opencv"
    
    def detect_from_image(
        self,
        image: np.ndarray
    ) -> List[DetectionResult]:
        """
        اكتشاف كل أحجار الدومينو في الصورة
        """
        if self.method == "yolo":
            return self._detect_yolo(image)
        return self._detect_opencv(image)
    
    def detect_from_camera(
        self
    ) -> List[DetectionResult]:
        """
        اكتشاف من الكاميرا مباشرة
        """
        cap = cv2.VideoCapture(0)
        
        print("📷 اضغط SPACE لالتقاط الصورة، Q للخروج")
        
        results = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # عرض مباشر مع تحديد الأحجار
            display = frame.copy()
            
            # اكتشاف سريع للعرض
            contours = self.preprocessor.find_domino_contours(
                frame
            )
            for cnt in contours:
                cv2.drawContours(
                    display, [cnt], -1, (0, 255, 0), 2
                )
            
            cv2.imshow("Domino Detector", display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):  # التقاط
                results = self.detect_from_image(frame)
                break
            elif key == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        return results
    
    def _detect_opencv(
        self,
        image: np.ndarray
    ) -> List[DetectionResult]:
        """اكتشاف بـ OpenCV"""
        processed = self.preprocessor.preprocess(image)
        contours = self.preprocessor.find_domino_contours(
            processed
        )
        
        results = []
        
        for cnt in contours:
            try:
                left_half, right_half = (
                    self.preprocessor.extract_tile_image(
                        processed, cnt
                    )
                )
                
                high, low = self.pip_counter.count_tile(
                    left_half, right_half
                )
                
                if 0 <= high <= 6 and 0 <= low <= 6:
                    x, y, w, h = cv2.boundingRect(cnt)
                    
                    tile = DominoTile(high, low)
                    
                    results.append(DetectionResult(
                        tile=tile,
                        confidence=0.75,  # ثابت لـ OpenCV
                        bounding_box=(x, y, w, h),
                        image_crop=processed[y:y+h, x:x+w]
                    ))
            except Exception:
                continue
        
        return results
    
    def _detect_yolo(
        self,
        image: np.ndarray
    ) -> List[DetectionResult]:
        """اكتشاف بـ YOLO"""
        predictions = self.yolo_model(image, conf=0.5)
        
        results = []
        
        for pred in predictions[0].boxes:
            # YOLO يعطي مباشرة الحجر ورقمه
            cls = int(pred.cls)
            conf = float(pred.conf)
            x1, y1, x2, y2 = map(int, pred.xyxy[0])
            
            # تحويل class index لأرقام الحجر
            high, low = self._class_to_tile(cls)
            
            tile = DominoTile(high, low)
            
            results.append(DetectionResult(
                tile=tile,
                confidence=conf,
                bounding_box=(x1, y1, x2-x1, y2-y1),
                image_crop=image[y1:y2, x1:x2]
            ))
        
        return results
    
    def _class_to_tile(
        self, 
        class_idx: int
    ) -> Tuple[int, int]:
        """
        تحويل رقم الفئة من YOLO لأرقام الحجر
        الترتيب: 0|0, 1|0, 1|1, 2|0, 2|1, 2|2, ...
        """
        idx = 0
        for i in range(7):
            for j in range(i + 1):
                if idx == class_idx:
                    return (i, j)
                idx += 1
        return (0, 0)
    
    def display_results(
        self,
        image: np.ndarray,
        results: List[DetectionResult]
    ):
        """عرض النتائج على الصورة"""
        display = image.copy()
        
        for r in results:
            x, y, w, h = r.bounding_box
            
            # لون حسب الثقة
            if r.confidence >= 0.8:
                color = (0, 255, 0)    # أخضر
            elif r.confidence >= 0.6:
                color = (0, 255, 255)  # أصفر
            else:
                color = (0, 0, 255)    # أحمر
            
            cv2.rectangle(
                display, (x, y), (x+w, y+h), color, 2
            )
            
            label = f"{r.tile} ({r.confidence:.0%})"
            cv2.putText(
                display, label,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6, color, 2
            )
        
        cv2.imshow("Detection Results", display)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
