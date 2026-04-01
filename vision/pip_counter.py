# vision/pip_counter.py
"""
عدّ النقاط (Pips) على كل نصف من حجر الدومينو
"""
import cv2
import numpy as np
from typing import Tuple, Optional


class PipCounter:
    """
    عدّ نقاط الدومينو باستخدام معالجة الصور
    
    الفكرة:
    1. تحويل لأبيض وأسود
    2. إيجاد الدوائر (النقاط)
    3. عدّها
    """
    
    def __init__(
        self,
        min_pip_radius: int = 5,
        max_pip_radius: int = 20,
        min_circularity: float = 0.7
    ):
        self.min_radius = min_pip_radius
        self.max_radius = max_pip_radius
        self.min_circularity = min_circularity
    
    def count_pips(self, half_image: np.ndarray) -> int:
        """
        عدّ النقاط في نصف حجر الدومينو
        """
        if half_image is None or half_image.size == 0:
            return -1
        
        # تحويل لرمادي
        if len(half_image.shape) == 3:
            gray = cv2.cvtColor(half_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = half_image.copy()
        
        # Method 1: Hough Circles
        count1 = self._count_by_hough(gray)
        
        # Method 2: Contour Analysis
        count2 = self._count_by_contours(gray)
        
        # Method 3: Blob Detection
        count3 = self._count_by_blobs(gray)
        
        # التصويت بالأغلبية
        counts = [count1, count2, count3]
        # نأخذ الأكثر تكراراً
        from collections import Counter
        most_common = Counter(counts).most_common(1)
        
        if most_common:
            return most_common[0][0]
        
        return count2  # الافتراضي
    
    def _count_by_hough(self, gray: np.ndarray) -> int:
        """عدّ بطريقة Hough Circles"""
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=self.min_radius * 2,
            param1=50,
            param2=30,
            minRadius=self.min_radius,
            maxRadius=self.max_radius
        )
        
        if circles is not None:
            return len(circles[0])
        return 0
    
    def _count_by_contours(self, gray: np.ndarray) -> int:
        """عدّ بطريقة تحليل الحدود"""
        # Threshold
        _, thresh = cv2.threshold(
            gray, 0, 255, 
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        
        # تنظيف
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(
            thresh, cv2.MORPH_OPEN, kernel
        )
        
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        pip_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            perimeter = cv2.arcLength(cnt, True)
            
            if perimeter == 0:
                continue
            
            # اختبار الدائرية
            circularity = (
                4 * np.pi * area / (perimeter ** 2)
            )
            
            if (
                circularity >= self.min_circularity and
                area >= np.pi * self.min_radius ** 2 * 0.5 and
                area <= np.pi * self.max_radius ** 2 * 1.5
            ):
                pip_count += 1
        
        return min(pip_count, 6)  # أقصى 6
    
    def _count_by_blobs(self, gray: np.ndarray) -> int:
        """عدّ بطريقة Blob Detection"""
        params = cv2.SimpleBlobDetector_Params()
        
        params.filterByArea = True
        params.minArea = np.pi * self.min_radius ** 2 * 0.5
        params.maxArea = np.pi * self.max_radius ** 2 * 2
        
        params.filterByCircularity = True
        params.minCircularity = self.min_circularity
        
        params.filterByInertia = True
        params.minInertiaRatio = 0.5
        
        params.filterByConvexity = True
        params.minConvexity = 0.8
        
        # عكس الصورة (نقاط سوداء على خلفية بيضاء)
        inverted = cv2.bitwise_not(gray)
        
        detector = cv2.SimpleBlobDetector_create(params)
        keypoints = detector.detect(inverted)
        
        return min(len(keypoints), 6)
    
    def count_tile(
        self,
        left_half: np.ndarray,
        right_half: np.ndarray
    ) -> Tuple[int, int]:
        """
        عدّ نقاط حجر كامل
        
        Returns:
            (نقاط النصف الأيسر, نقاط النصف الأيمن)
        """
        left_count = self.count_pips(left_half)
        right_count = self.count_pips(right_half)
        
        # ترتيب (الأكبر أولاً)
        high = max(left_count, right_count)
        low = min(left_count, right_count)
        
        return high, low
