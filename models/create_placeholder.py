

"""
إنشاء ملف placeholder للنموذج
يُستخدم فقط لتوضيح هيكل المشروع
"""
import os
import json

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

def create_model_info():
    """إنشاء ملف معلومات النموذج"""
    info = {
        "model_name": "domino_detector_yolov8",
        "version": "0.1.0",
        "description": (
            "YOLOv8 model trained to detect "
            "domino tiles and their pip values"
        ),
        "num_classes": 28,
        "classes": [
            f"{i}-{j}" 
            for i in range(7) 
            for j in range(i + 1)
        ],
        "input_size": [640, 640],
        "framework": "ultralytics",
        "status": "placeholder - needs training",
        "training_instructions": (
            "See README.md in this directory"
        )
    }
    
    filepath = os.path.join(MODEL_DIR, "model_info.json")
    with open(filepath, 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"✅ تم إنشاء {filepath}")
    return info


if __name__ == "__main__":
    create_model_info()
