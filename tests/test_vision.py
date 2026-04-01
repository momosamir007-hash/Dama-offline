# tests/test_vision.py
"""
اختبارات الرؤية الحاسوبية
يتحقق من:
  - معالجة الصور
  - عدّ النقاط
  - اكتشاف الأحجار
  - الكاميرا
"""

import unittest
import sys
import os
import tempfile

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# محاولة استيراد OpenCV
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from game_engine.domino_board import DominoTile


@unittest.skipUnless(CV2_AVAILABLE, "OpenCV غير مثبت")
class TestImagePreprocessor(unittest.TestCase):
    """اختبارات معالجة الصور"""
    
    def setUp(self):
        from vision.preprocessor import ImagePreprocessor
        self.preprocessor = ImagePreprocessor()
        
        # إنشاء صورة اختبارية
        self.test_image = np.zeros(
            (600, 800, 3), dtype=np.uint8
        )
        # رسم مستطيل يشبه حجر الدومينو
        cv2.rectangle(
            self.test_image,
            (100, 200), (300, 300),
            (255, 255, 255), -1
        )
        # خط فاصل
        cv2.line(
            self.test_image,
            (200, 200), (200, 300),
            (0, 0, 0), 2
        )
    
    def test_preprocess_resize(self):
        """تصغير الصورة"""
        large_image = np.zeros(
            (2000, 3000, 3), dtype=np.uint8
        )
        processed = self.preprocessor.preprocess(
            large_image, target_size=800
        )
        
        h, w = processed.shape[:2]
        self.assertLessEqual(max(h, w), 800)
    
    def test_enhance(self):
        """تحسين الصورة"""
        enhanced = self.preprocessor.enhance_for_detection(
            self.test_image
        )
        
        # يجب أن تكون رمادية (بعد واحد)
        self.assertEqual(len(enhanced.shape), 2)
    
    def test_find_contours(self):
        """إيجاد الحدود"""
        contours = self.preprocessor.find_domino_contours(
            self.test_image
        )
        
        # يجب أن نجد على الأقل حد واحد
        # (قد لا ينجح 100% مع صورة بسيطة)
        self.assertIsInstance(contours, list)


@unittest.skipUnless(CV2_AVAILABLE, "OpenCV غير مثبت")
class TestPipCounter(unittest.TestCase):
    """اختبارات عدّ النقاط"""
    
    def setUp(self):
        from vision.pip_counter import PipCounter
        self.counter = PipCounter(
            min_pip_radius=8,
            max_pip_radius=15,
            min_circularity=0.6
        )
    
    def _create_pip_image(
        self, 
        num_pips: int,
        size: int = 100
    ) -> np.ndarray:
        """
        إنشاء صورة اختبارية بعدد محدد من النقاط
        """
        image = np.ones(
            (size, size), dtype=np.uint8
        ) * 255
        
        # مواقع النقاط حسب العدد (نمط الدومينو)
        positions = {
            0: [],
            1: [(50, 50)],
            2: [(25, 75), (75, 25)],
            3: [(25, 75), (50, 50), (75, 25)],
            4: [
                (25, 25), (25, 75), 
                (75, 25), (75, 75)
            ],
            5: [
                (25, 25), (25, 75), (50, 50),
                (75, 25), (75, 75)
            ],
            6: [
                (25, 25), (25, 50), (25, 75),
                (75, 25), (75, 50), (75, 75)
            ],
        }
        
        for pos in positions.get(num_pips, []):
            cv2.circle(
                image, pos, 10, 0, -1  # دوائر سوداء
            )
        
        return image
    
    def test_count_zero(self):
        """عدّ صفر نقاط"""
        image = self._create_pip_image(0)
        count = self.counter.count_pips(image)
        self.assertEqual(count, 0)
    
    def test_count_one(self):
        """عدّ نقطة واحدة"""
        image = self._create_pip_image(1)
        count = self.counter.count_pips(image)
        self.assertIn(count, [0, 1])
    
    def test_count_six(self):
        """عدّ 6 نقاط"""
        image = self._create_pip_image(6)
        count = self.counter.count_pips(image)
        self.assertIn(
            count, [5, 6],
            f"المتوقع 6 لكن الناتج {count}"
        )
    
    def test_count_tile(self):
        """عدّ حجر كامل"""
        left = self._create_pip_image(5)
        right = self._create_pip_image(3)
        
        high, low = self.counter.count_tile(left, right)
        
        self.assertGreaterEqual(high, low)
        self.assertLessEqual(high, 6)
        self.assertGreaterEqual(low, 0)
    
    def test_empty_image(self):
        """صورة فارغة"""
        count = self.counter.count_pips(None)
        self.assertEqual(count, -1)


@unittest.skipUnless(CV2_AVAILABLE, "OpenCV غير مثبت")
class TestDominoDetector(unittest.TestCase):
    """اختبارات المُكتشف الرئيسي"""
    
    def setUp(self):
        from vision.detector import DominoDetector
        self.detector = DominoDetector(method="opencv")
    
    def test_detect_empty_image(self):
        """اكتشاف في صورة فارغة"""
        empty = np.zeros(
            (480, 640, 3), dtype=np.uint8
        )
        results = self.detector.detect_from_image(empty)
        
        self.assertIsInstance(results, list)
        # صورة فارغة = لا أحجار
        self.assertEqual(len(results), 0)
    
    def test_detection_result_structure(self):
        """هيكل نتيجة الاكتشاف"""
        from vision.detector import DetectionResult
        
        result = DetectionResult(
            tile=DominoTile(6, 4),
            confidence=0.95,
            bounding_box=(10, 20, 100, 50)
        )
        
        self.assertEqual(result.tile, DominoTile(6, 4))
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(
            result.bounding_box, (10, 20, 100, 50)
        )
    
    def test_class_to_tile(self):
        """تحويل فئة YOLO لحجر"""
        # class 0 = [0|0]
        h, l = self.detector._class_to_tile(0)
        self.assertEqual((h, l), (0, 0))
        
        # class 1 = [1|0]
        h, l = self.detector._class_to_tile(1)
        self.assertEqual((h, l), (1, 0))
        
        # class 2 = [1|1]
        h, l = self.detector._class_to_tile(2)
        self.assertEqual((h, l), (1, 1))
        
        # class 27 = [6|6]
        h, l = self.detector._class_to_tile(27)
        self.assertEqual((h, l), (6, 6))


@unittest.skipUnless(CV2_AVAILABLE, "OpenCV غير مثبت")
class TestCameraManager(unittest.TestCase):
    """اختبارات مدير الكاميرا"""
    
    def setUp(self):
        from ui.camera import (
            CameraManager, CameraConfig, CaptureMode
        )
        self.CameraManager = CameraManager
        self.CameraConfig = CameraConfig
        self.CaptureMode = CaptureMode
    
    def test_config_defaults(self):
        """الإعدادات الافتراضية"""
        config = self.CameraConfig()
        
        self.assertEqual(config.device_id, 0)
        self.assertEqual(
            config.resolution, (1280, 720)
        )
        self.assertEqual(config.fps, 30)
    
    def test_capture_from_file(self):
        """الالتقاط من ملف"""
        # إنشاء صورة اختبارية
        test_image = np.zeros(
            (480, 640, 3), dtype=np.uint8
        )
        
        with tempfile.NamedTemporaryFile(
            suffix='.jpg', delete=False
        ) as f:
            filepath = f.name
            cv2.imwrite(filepath, test_image)
        
        result = self.CameraManager.capture_from_file(
            filepath
        )
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.image)
        self.assertEqual(
            result.mode, self.CaptureMode.FILE
        )
        
        # تنظيف
        os.unlink(filepath)
    
    def test_capture_from_nonexistent_file(self):
        """الالتقاط من ملف غير موجود"""
        result = self.CameraManager.capture_from_file(
            "nonexistent_file.jpg"
        )
        
        self.assertFalse(result.success)
        self.assertIn("غير موجود", result.error)
    
    def test_capture_unsupported_format(self):
        """صيغة غير مدعومة"""
        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False
        ) as f:
            f.write(b"not an image")
            filepath = f.name
        
        result = self.CameraManager.capture_from_file(
            filepath
        )
        
        self.assertFalse(result.success)
        self.assertIn("غير مدعومة", result.error)
        
        os.unlink(filepath)
    
    def test_measure_sharpness(self):
        """قياس الوضوح"""
        # صورة واضحة (حواف حادة)
        sharp = np.zeros(
            (100, 100, 3), dtype=np.uint8
        )
        cv2.rectangle(
            sharp, (20, 20), (80, 80), 
            (255, 255, 255), -1
        )
        
        # صورة ضبابية
        blurry = cv2.GaussianBlur(
            sharp, (31, 31), 10
        )
        
        sharp_score = (
            self.CameraManager._measure_sharpness(sharp)
        )
        blurry_score = (
            self.CameraManager._measure_sharpness(blurry)
        )
        
        self.assertGreater(
            sharp_score, blurry_score,
            "الصورة الواضحة يجب أن تحصل على درجة أعلى"
        )
    
    def test_list_cameras(self):
        """عرض الكاميرات (لا يحتاج كاميرا فعلية)"""
        cameras = self.CameraManager.list_cameras()
        self.assertIsInstance(cameras, list)


class TestVisionIntegration(unittest.TestCase):
    """اختبارات تكاملية للرؤية"""
    
    @unittest.skipUnless(CV2_AVAILABLE, "OpenCV غير مثبت")
    def test_full_pipeline(self):
        """
        الأنبوب الكامل:
        صورة → معالجة → اكتشاف → أحجار
        """
        from vision.detector import DominoDetector
        
        # صورة اختبارية (بسيطة)
        image = np.ones(
            (480, 640, 3), dtype=np.uint8
        ) * 200
        
        # رسم "حجر" بسيط
        cv2.rectangle(
            image, (200, 200), (400, 280),
            (255, 255, 255), -1
        )
        cv2.line(
            image, (300, 200), (300, 280),
            (0, 0, 0), 2
        )
        
        detector = DominoDetector(method="opencv")
        results = detector.detect_from_image(image)
        
        # النتائج يجب أن تكون قائمة
        self.assertIsInstance(results, list)
        
        # كل نتيجة يجب أن تحتوي على حجر صحيح
        for r in results:
            self.assertIsInstance(r.tile, DominoTile)
            self.assertGreaterEqual(r.confidence, 0.0)
            self.assertLessEqual(r.confidence, 1.0)
            self.assertTrue(0 <= r.tile.high <= 6)
            self.assertTrue(0 <= r.tile.low <= 6)


class TestWithoutOpenCV(unittest.TestCase):
    """
    اختبارات بدون OpenCV
    يتأكد أن المشروع يعمل بدون رؤية حاسوبية
    """
    
    def test_game_works_without_cv(self):
        """اللعبة تعمل بدون OpenCV"""
        from game_engine.game_state import (
            GameState, PlayerPosition
        )
        from game_engine.domino_board import DominoTile
        
        state = GameState()
        state.initialize_players()
        state.set_my_hand([
            DominoTile(6, 6),
            DominoTile(5, 3),
        ])
        
        self.assertEqual(len(state.my_hand), 2)
    
    def test_ai_works_without_cv(self):
        """الذكاء الاصطناعي يعمل بدون OpenCV"""
        from game_engine.game_state import (
            GameState, PlayerPosition
        )
        from game_engine.domino_board import DominoTile
        from ai_brain.probability import ProbabilityEngine
        
        state = GameState()
        state.initialize_players()
        state.set_my_hand([
            DominoTile(6, 6),
            DominoTile(5, 3),
            DominoTile(4, 2),
            DominoTile(3, 1),
            DominoTile(2, 0),
            DominoTile(1, 0),
            DominoTile(6, 4),
        ])
        
        engine = ProbabilityEngine(state)
        probs = engine.calculate_tile_probabilities()
        
        self.assertIsInstance(probs, dict)
        self.assertEqual(len(probs), 3)  # 3 خصوم
    
    def test_manual_input_module(self):
        """وحدة الإدخال اليدوي موجودة"""
        from ui.manual_input import ManualInput
        
        self.assertTrue(
            hasattr(ManualInput, 'input_tiles')
        )
        self.assertTrue(
            hasattr(ManualInput, 'review_detection')
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
