# config.py
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class GameConfig:
    max_pip: int = 6                    # أعلى رقم (6|6)
    num_players: int = 4                # عدد اللاعبين
    hand_size: int = 7                  # أحجار كل لاعب
    scoring_method: str = "egyptian"    # طريقة الحساب
    
    # أوزان الاستراتيجية
    weights: Dict[str, float] = field(default_factory=lambda: {
        'control': 0.35,       # التحكم بالأرقام
        'blocking': 0.25,      # القفل
        'counting': 0.20,      # حساب النقاط
        'diversity': 0.20      # تنويع الخيارات
    })
    
    # إعدادات MCTS
    mcts_simulations: int = 5000
    mcts_exploration: float = 1.414    # √2
    mcts_time_limit: float = 3.0       # ثوانٍ
