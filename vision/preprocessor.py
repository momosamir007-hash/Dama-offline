# vision/preprocessor.py
"""
معالجة الصور قبل اكتشاف الأحجار
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional


class ImagePreprocessor:
    """
    تحضير الصورة لاكتشاف أحجار الدومينو
    """
    
    @staticmethod
    def preprocess(
        image: np.ndarray,
        target_size: int = 800
    ) -> np.ndarray:
        """المعالجة الأساسية"""
        # تصغير مع الحفاظ على النسبة
        h, w = image.shape[:2]
        scale = target_size / max(h, w)
        if scale < 1:
            image = cv2.resize(
                image, None, fx=scale, fy=scale
            )
        
        return image
    
    @staticmethod
    def enhance_for_detection(image: np.ndarray) -> np.ndarray:
        """تحسين الصورة لاكتشاف أفضل"""
        # تحويل لرمادي
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # تحسين التباين
        clahe = cv2.createCLAHE(
            clipLimit=2.0, tileGridSize=(8, 8)
        )
        enhanced = clahe.apply(gray)
        
        # تنعيم خفيف لإزالة الضوضاء
        blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
        
        return blurred
    
    @staticmethod
    def find_domino_contours(
        image: np.ndarray
    ) -> List[np.ndarray]:
        """
        إيجاد حدود أحجار الدومينو
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        
        # حد تكيفي
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )
        
        # تنظيف
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(
            thresh, cv2.MORPH_CLOSE, kernel, iterations=2
        )
        thresh = cv2.morphologyEx(
            thresh, cv2.MORPH_OPEN, kernel, iterations=1
        )
        
        # إيجاد الحدود
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # فلترة - نبقي فقط المستطيلات بنسبة أبعاد معقولة
        valid_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 1000:  # صغير جداً
                continue
            
            rect = cv2.minAreaRect(cnt)
            w, h = rect[1]
            if w == 0 or h == 0:
                continue
            
            aspect_ratio = max(w, h) / min(w, h)
            
            # حجر الدومينو: نسبة أبعاد ≈ 2:1
            if 1.5 <= aspect_ratio <= 2.8:
                valid_contours.append(cnt)
        
        return valid_contours
    
    @staticmethod
    def extract_tile_image(
        image: np.ndarray,
        contour: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        قص صورة حجر واحد وتصحيح الدوران
        إرجاع: (النصف العلوي, النصف السفلي)
        """
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        
        # تصحيح الدوران
        width = int(rect[1][0])
        height = int(rect[1][1])
        
        if width < height:
            width, height = height, width
        
        src_pts = box.astype("float32")
        dst_pts = np.array([
            [0, height - 1],
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(image, M, (width, height))
        
        # تقسيم لنصفين
        mid = width // 2
        left_half = warped[:, :mid]
        right_half = warped[:, mid:]
        
        return left_half, right_half
