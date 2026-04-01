# ai_brain/trainer.py
"""
نظام تدريب الذكاء الاصطناعي
باستخدام التعلم المعزز (Reinforcement Learning)
والمحاكاة الذاتية (Self-Play)

الهدف: تدريب نموذج يتعلم أفضل استراتيجيات الدومينو
من خلال لعب ملايين المباريات ضد نفسه
"""

from __future__ import annotations
import json
import os
import time
import random
import pickle
from dataclasses import dataclass, field
from typing import (
    List, Dict, Optional, Tuple, 
    Callable, Any
)
from collections import defaultdict
from pathlib import Path
import numpy as np

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo, Move
)
from game_engine.rules import DominoRules, GameMode
from ai_brain.mcts import MCTSEngine
from config import GameConfig


# ──────────────────────────────────────────────
# إعدادات التدريب
# ──────────────────────────────────────────────

@dataclass
class TrainingConfig:
    """إعدادات جلسة التدريب"""
    num_episodes: int = 10000           # عدد المباريات
    batch_size: int = 64                # حجم الدفعة
    learning_rate: float = 0.001        # معدل التعلم
    discount_factor: float = 0.95       # عامل الخصم γ
    epsilon_start: float = 1.0          # استكشاف أولي
    epsilon_end: float = 0.05           # استكشاف نهائي
    epsilon_decay: float = 0.9995       # معدل تناقص الاستكشاف
    
    # MCTS أثناء التدريب
    mcts_sims_training: int = 200       # محاكاات أقل للسرعة
    mcts_sims_evaluation: int = 1000    # محاكاات أكثر للتقييم
    
    # حفظ النموذج
    save_interval: int = 500            # حفظ كل X مباراة
    eval_interval: int = 100            # تقييم كل X مباراة
    model_dir: str = "models/trained"
    log_dir: str = "logs"
    
    # التقييم
    eval_games: int = 50                # عدد مباريات التقييم


@dataclass 
class Experience:
    """تجربة واحدة (state, action, reward, next_state)"""
    state_features: np.ndarray
    action_index: int
    reward: float
    next_state_features: Optional[np.ndarray]
    done: bool


@dataclass
class TrainingStats:
    """إحصائيات التدريب"""
    episode: int = 0
    total_wins: int = 0
    total_losses: int = 0
    total_draws: int = 0
    total_dominos: int = 0         # فوز بالدومينو (تخليص)
    total_locks: int = 0           # فوز بالقفل
    
    win_rates: List[float] = field(default_factory=list)
    avg_rewards: List[float] = field(default_factory=list)
    epsilons: List[float] = field(default_factory=list)
    episode_lengths: List[int] = field(default_factory=list)
    
    best_win_rate: float = 0.0
    
    @property
    def current_win_rate(self) -> float:
        total = (
            self.total_wins + 
            self.total_losses + 
            self.total_draws
        )
        if total == 0:
            return 0.0
        return self.total_wins / total
    
    def display(self) -> str:
        return (
            f"\n{'═' * 50}\n"
            f"📊 إحصائيات التدريب - الحلقة {self.episode}\n"
            f"{'═' * 50}\n"
            f"  فوز: {self.total_wins} | "
            f"خسارة: {self.total_losses} | "
            f"تعادل: {self.total_draws}\n"
            f"  نسبة الفوز: {self.current_win_rate:.1%}\n"
            f"  أفضل نسبة: {self.best_win_rate:.1%}\n"
            f"  دومينو: {self.total_dominos} | "
            f"قفل: {self.total_locks}\n"
            f"{'═' * 50}"
        )


# ──────────────────────────────────────────────
# استخراج الميزات
# ──────────────────────────────────────────────

class FeatureExtractor:
    """
    يحول حالة اللعبة لشعاع أرقام (Feature Vector)
    يفهمه نموذج الذكاء الاصطناعي
    
    الميزات:
    1. أحجاري (28 خانة: 0/1 لكل حجر)
    2. أطراف الطاولة (2 قيمة)
    3. عدد أحجار كل خصم (3 قيم)
    4. الأرقام المدقوقة لكل خصم (3 × 7)
    5. تكرار كل رقم في يدي (7 قيم)
    6. عدد الأحجار المتبقية لكل رقم (7 قيم)
    7. هل أملك دبل لكل رقم (7 قيم)
    8. عدد الحركات المتاحة (1 قيمة)
    9. الدور الحالي (4 قيم one-hot)
    """
    
    # ترتيب ثابت لكل الأحجار (28 حجر)
    TILE_INDEX: Dict[DominoTile, int] = {}
    
    @classmethod
    def _build_tile_index(cls):
        """بناء فهرس الأحجار"""
        if cls.TILE_INDEX:
            return
        idx = 0
        for i in range(7):
            for j in range(i, 7):
                tile = DominoTile(j, i)
                cls.TILE_INDEX[tile] = idx
                idx += 1
    
    @classmethod
    def extract(cls, state: GameState) -> np.ndarray:
        """
        استخراج شعاع الميزات من حالة اللعبة
        
        Returns:
            np.ndarray بحجم ~80 عنصر
        """
        cls._build_tile_index()
        
        features = []
        
        # 1. أحجاري (28 خانة)
        my_tiles = np.zeros(28)
        for tile in state.my_hand:
            if tile in cls.TILE_INDEX:
                my_tiles[cls.TILE_INDEX[tile]] = 1.0
        features.extend(my_tiles)
        
        # 2. أطراف الطاولة (2 قيمة: -1 لو فاضي)
        left = (
            state.board.left_end / 6.0 
            if state.board.left_end is not None 
            else -1.0
        )
        right = (
            state.board.right_end / 6.0 
            if state.board.right_end is not None 
            else -1.0
        )
        features.extend([left, right])
        
        # 3. عدد أحجار كل خصم (3 قيم: مطبّعة)
        for pos in [
            PlayerPosition.WEST,
            PlayerPosition.NORTH, 
            PlayerPosition.EAST
        ]:
            count = state.players[pos].tiles_count / 7.0
            features.append(count)
        
        # 4. الأرقام المدقوقة (3 × 7 = 21 خانة)
        for pos in [
            PlayerPosition.WEST,
            PlayerPosition.NORTH, 
            PlayerPosition.EAST
        ]:
            passed = state.players[pos].passed_values
            for num in range(7):
                features.append(
                    1.0 if num in passed else 0.0
                )
        
        # 5. تكرار كل رقم في يدي (7 قيم)
        my_counts = [0] * 7
        for tile in state.my_hand:
            my_counts[tile.high] += 1
            if tile.high != tile.low:
                my_counts[tile.low] += 1
        features.extend([c / 7.0 for c in my_counts])
        
        # 6. عدد الأحجار المتبقية لكل رقم (7 قيم)
        remaining = state.get_remaining_count_per_value()
        for num in range(7):
            features.append(
                remaining.get(num, 0) / 8.0
            )
        
        # 7. هل أملك دبل لكل رقم (7 قيم)
        for num in range(7):
            has_double = DominoTile(num, num) in state.my_hand
            features.append(1.0 if has_double else 0.0)
        
        # 8. عدد الحركات المتاحة (1 قيمة)
        valid_moves = state.get_valid_moves(
            PlayerPosition.SOUTH
        )
        real_moves = [m for m in valid_moves if not m.is_pass]
        features.append(len(real_moves) / 14.0)
        
        # 9. الدور الحالي (4 قيم one-hot)
        turn_onehot = [0.0] * 4
        turn_onehot[state.current_turn.value] = 1.0
        features.extend(turn_onehot)
        
        return np.array(features, dtype=np.float32)
    
    @classmethod
    def feature_size(cls) -> int:
        """حجم شعاع الميزات"""
        return 28 + 2 + 3 + 21 + 7 + 7 + 7 + 1 + 4  # = 80


# ──────────────────────────────────────────────
# Q-Table (جدول القيم)
# ──────────────────────────────────────────────

class QTable:
    """
    جدول Q بسيط مع تجزئة الحالة
    
    بدل جدول ضخم: نستخدم تجزئة ذكية
    للحالة (state hashing) لتقليل الحجم
    """
    
    def __init__(
        self, 
        default_value: float = 0.0,
        learning_rate: float = 0.1,
        discount: float = 0.95
    ):
        self.table: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(lambda: default_value)
        )
        self.lr = learning_rate
        self.discount = discount
        self.visit_count: Dict[str, int] = defaultdict(int)
    
    def _state_key(self, features: np.ndarray) -> str:
        """
        تحويل الميزات لمفتاح مضغوط
        نقرّب القيم لتقليل عدد الحالات
        """
        # تقريب لأقرب 0.2
        rounded = np.round(features * 5) / 5
        return rounded.tobytes().hex()[:32]
    
    def _action_key(self, move: Move) -> str:
        """تحويل الحركة لمفتاح"""
        if move.is_pass:
            return "pass"
        
        dir_str = (
            move.direction.value 
            if move.direction else "none"
        )
        return f"{move.tile.high}-{move.tile.low}_{dir_str}"
    
    def get_value(
        self, 
        features: np.ndarray, 
        move: Move
    ) -> float:
        """قراءة قيمة Q"""
        sk = self._state_key(features)
        ak = self._action_key(move)
        return self.table[sk][ak]
    
    def get_best_action(
        self,
        features: np.ndarray,
        valid_moves: List[Move]
    ) -> Move:
        """أفضل حركة حسب جدول Q"""
        sk = self._state_key(features)
        
        best_move = valid_moves[0]
        best_value = float('-inf')
        
        for move in valid_moves:
            ak = self._action_key(move)
            value = self.table[sk][ak]
            if value > best_value:
                best_value = value
                best_move = move
        
        return best_move
    
    def update(
        self,
        features: np.ndarray,
        move: Move,
        reward: float,
        next_features: Optional[np.ndarray],
        next_valid_moves: List[Move],
        done: bool
    ):
        """
        تحديث قيمة Q باستخدام Q-Learning
        
        Q(s,a) ← Q(s,a) + α[r + γ·max Q(s',a') - Q(s,a)]
        """
        sk = self._state_key(features)
        ak = self._action_key(move)
        
        current_q = self.table[sk][ak]
        
        if done or next_features is None:
            target = reward
        else:
            # أفضل قيمة Q للحالة التالية
            next_sk = self._state_key(next_features)
            max_next_q = max(
                self.table[next_sk][self._action_key(m)]
                for m in next_valid_moves
            ) if next_valid_moves else 0.0
            
            target = reward + self.discount * max_next_q
        
        # تحديث
        self.table[sk][ak] = (
            current_q + self.lr * (target - current_q)
        )
        
        self.visit_count[sk] += 1
    
    def save(self, filepath: str):
        """حفظ الجدول"""
        data = {
            'table': dict(self.table),
            'visits': dict(self.visit_count),
            'lr': self.lr,
            'discount': self.discount
        }
        # تحويل defaultdict لـ dict عادي
        serializable = {}
        for sk, actions in data['table'].items():
            serializable[sk] = dict(actions)
        data['table'] = serializable
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"💾 تم حفظ الجدول: {filepath}")
        print(
            f"   حالات فريدة: "
            f"{len(self.table):,}"
        )
    
    def load(self, filepath: str):
        """تحميل الجدول"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.table = defaultdict(
            lambda: defaultdict(float)
        )
        for sk, actions in data['table'].items():
            for ak, val in actions.items():
                self.table[sk][ak] = val
        
        self.visit_count = defaultdict(int)
        self.visit_count.update(data.get('visits', {}))
        self.lr = data.get('lr', self.lr)
        self.discount = data.get('discount', self.discount)
        
        print(f"📂 تم تحميل الجدول: {filepath}")
        print(
            f"   حالات فريدة: "
            f"{len(self.table):,}"
        )


# ──────────────────────────────────────────────
# المدرب الرئيسي
# ──────────────────────────────────────────────

class DominoTrainer:
    """
    مدرب الذكاء الاصطناعي
    
    يدير عملية التدريب الكاملة:
    1. تشغيل مباريات ذاتية (Self-Play)
    2. جمع التجارب
    3. تحديث النموذج
    4. تقييم الأداء
    5. حفظ النموذج
    """
    
    def __init__(
        self,
        config: TrainingConfig = None,
        game_config: GameConfig = None
    ):
        self.config = config or TrainingConfig()
        self.game_config = game_config or GameConfig()
        self.rules = DominoRules(mode=GameMode.EGYPTIAN)
        
        # نموذج التعلم
        self.q_table = QTable(
            learning_rate=self.config.learning_rate,
            discount=self.config.discount_factor
        )
        
        # الإحصائيات
        self.stats = TrainingStats()
        
        # Epsilon للاستكشاف
        self.epsilon = self.config.epsilon_start
        
        # تأكد من وجود المجلدات
        os.makedirs(self.config.model_dir, exist_ok=True)
        os.makedirs(self.config.log_dir, exist_ok=True)
    
    # ──────────────────────────────────────────
    # حلقة التدريب الرئيسية
    # ──────────────────────────────────────────
    
    def train(self):
        """
        حلقة التدريب الرئيسية
        """
        print("\n" + "🏋️" * 20)
        print("بدء التدريب")
        print(f"عدد الحلقات: {self.config.num_episodes:,}")
        print(f"Epsilon: {self.epsilon:.3f}")
        print("🏋️" * 20)
        
        start_time = time.time()
        
        for episode in range(1, self.config.num_episodes + 1):
            self.stats.episode = episode
            
            # 1. لعب مباراة واحدة
            experiences, result = self._play_one_game()
            
            # 2. تحديث النموذج
            self._learn_from_experiences(experiences)
            
            # 3. تحديث الإحصائيات
            self._update_stats(result)
            
            # 4. تناقص Epsilon
            self.epsilon = max(
                self.config.epsilon_end,
                self.epsilon * self.config.epsilon_decay
            )
            self.stats.epsilons.append(self.epsilon)
            
            # 5. تقييم دوري
            if episode % self.config.eval_interval == 0:
                win_rate = self._evaluate()
                self.stats.win_rates.append(win_rate)
                
                elapsed = time.time() - start_time
                speed = episode / elapsed
                
                print(
                    f"[{episode:6d}/{self.config.num_episodes}] "
                    f"فوز: {win_rate:.1%} | "
                    f"ε: {self.epsilon:.3f} | "
                    f"سرعة: {speed:.0f} لعبة/ث | "
                    f"حالات: {len(self.q_table.table):,}"
                )
            
            # 6. حفظ دوري
            if episode % self.config.save_interval == 0:
                self._save_checkpoint(episode)
        
        # حفظ نهائي
        self._save_checkpoint("final")
        
        total_time = time.time() - start_time
        print(f"\n✅ انتهى التدريب في {total_time:.0f} ثانية")
        print(self.stats.display())
    
    # ──────────────────────────────────────────
    # لعب مباراة واحدة
    # ──────────────────────────────────────────
    
    def _play_one_game(
        self
    ) -> Tuple[List[Experience], str]:
        """
        لعب مباراة كاملة وجمع التجارب
        
        Returns:
            (قائمة التجارب, النتيجة: "win"/"loss"/"draw")
        """
        state = self._setup_random_game()
        experiences = []
        move_count = 0
        max_moves = 200
        
        while (
            not state.is_game_over and 
            move_count < max_moves
        ):
            current = state.current_turn
            
            # استخراج الميزات قبل الحركة
            features = FeatureExtractor.extract(state)
            
            # اختيار الحركة
            valid_moves = state.get_valid_moves(current)
            
            if current == PlayerPosition.SOUTH:
                # نحن: نستخدم epsilon-greedy
                move = self._choose_move_training(
                    features, valid_moves
                )
                action_idx = valid_moves.index(move)
            else:
                # الخصوم: عشوائي ذكي
                move = self._opponent_move(
                    valid_moves, state
                )
                action_idx = 0
            
            # تطبيق الحركة
            state.apply_move(move)
            move_count += 1
            
            # استخراج الميزات بعد الحركة
            next_features = FeatureExtractor.extract(state)
            
            # حساب المكافأة الفورية
            reward = self._calculate_reward(
                move, state, current
            )
            
            # تسجيل التجربة (فقط لحركاتنا)
            if current == PlayerPosition.SOUTH:
                experiences.append(Experience(
                    state_features=features,
                    action_index=action_idx,
                    reward=reward,
                    next_state_features=next_features,
                    done=state.is_game_over
                ))
        
        # مكافأة نهائية
        result = self._get_game_result(state)
        final_reward = self._final_reward(result)
        
        # تحديث المكافأة الأخيرة
        if experiences:
            experiences[-1].reward += final_reward
            experiences[-1].done = True
        
        return experiences, result
    
    def _setup_random_game(self) -> GameState:
        """إعداد مباراة بتوزيع عشوائي"""
        state = GameState()
        state.initialize_players()
        
        # توزيع كل الأحجار عشوائياً
        all_tiles = list(state.ALL_TILES)
        random.shuffle(all_tiles)
        
        positions = list(PlayerPosition)
        for i, pos in enumerate(positions):
            hand = all_tiles[i * 7:(i + 1) * 7]
            state.players[pos].hand = hand
            state.players[pos].tiles_count = len(hand)
        
        # تحديد من يبدأ (أعلى دبل)
        starter = self._find_starter(state)
        state.current_turn = starter
        
        return state
    
    def _find_starter(
        self, 
        state: GameState
    ) -> PlayerPosition:
        """إيجاد صاحب أعلى دبل"""
        best_pos = PlayerPosition.SOUTH
        best_double = -1
        
        for pos, player in state.players.items():
            for tile in player.hand:
                if tile.is_double and tile.high > best_double:
                    best_double = tile.high
                    best_pos = pos
        
        return best_pos
    
    def _choose_move_training(
        self,
        features: np.ndarray,
        valid_moves: List[Move]
    ) -> Move:
        """
        اختيار حركة أثناء التدريب
        باستخدام epsilon-greedy
        """
        if random.random() < self.epsilon:
            # استكشاف: حركة عشوائية
            return random.choice(valid_moves)
        else:
            # استغلال: أفضل حركة من الجدول
            return self.q_table.get_best_action(
                features, valid_moves
            )
    
    def _opponent_move(
        self,
        valid_moves: List[Move],
        state: GameState
    ) -> Move:
        """
        حركة الخصم أثناء التدريب
        مزيج من العشوائية والذكاء الأساسي
        """
        real_moves = [m for m in valid_moves if not m.is_pass]
        
        if not real_moves:
            return valid_moves[0]  # دق
        
        # 70% ذكي بسيط، 30% عشوائي
        if random.random() < 0.7:
            # تفضيل الأحجار الثقيلة والدبل
            scored = []
            for move in real_moves:
                score = move.tile.total
                if move.tile.is_double:
                    score += 3
                scored.append((score, move))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[0][1]
        
        return random.choice(real_moves)
    
    # ──────────────────────────────────────────
    # المكافآت
    # ──────────────────────────────────────────
    
    def _calculate_reward(
        self,
        move: Move,
        state: GameState,
        player: PlayerPosition
    ) -> float:
        """
        حساب المكافأة الفورية للحركة
        
        المكافآت:
        + لعب حجر ثقيل (التخلص من النقاط)
        + لعب دبل (تخليص الدبلات المزعجة)
        + قفل على الخصم
        - الدق (ما لقيت حجر)
        - ترك الخصم يقفلنا
        """
        if player != PlayerPosition.SOUTH:
            return 0.0
        
        reward = 0.0
        
        if move.is_pass:
            reward -= 2.0  # عقوبة الدق
        else:
            # مكافأة أساسية للعب
            reward += 0.5
            
            # مكافأة التخلص من حجر ثقيل
            reward += move.tile.total * 0.1
            
            # مكافأة لعب الدبل
            if move.tile.is_double:
                reward += 1.0
                if move.tile.total >= 8:
                    reward += 1.5  # دبل ثقيل
            
            # مكافأة تقليل عدد الأحجار
            remaining = len(state.my_hand)
            if remaining <= 2:
                reward += 2.0
            elif remaining <= 4:
                reward += 0.5
        
        return reward
    
    def _final_reward(self, result: str) -> float:
        """المكافأة النهائية"""
        rewards = {
            'win_domino': 20.0,     # فوز بالدومينو
            'win_lock': 10.0,       # فوز بالقفل
            'draw': 0.0,            # تعادل
            'loss_lock': -8.0,      # خسارة بالقفل
            'loss_domino': -15.0,   # خسارة بالدومينو
        }
        return rewards.get(result, 0.0)
    
    def _get_game_result(
        self, 
        state: GameState
    ) -> str:
        """تحديد نتيجة المباراة"""
        if not state.is_game_over:
            return 'draw'
        
        if state.winner in (
            PlayerPosition.SOUTH, 
            PlayerPosition.NORTH
        ):
            # هل فاز بالدومينو أو القفل
            winner_player = state.players[state.winner]
            if len(winner_player.hand) == 0:
                return 'win_domino'
            return 'win_lock'
        elif state.winner:
            winner_player = state.players[state.winner]
            if (
                hasattr(winner_player, 'hand') and
                len(winner_player.hand) == 0
            ):
                return 'loss_domino'
            return 'loss_lock'
        
        return 'draw'
    
    # ──────────────────────────────────────────
    # التعلم
    # ──────────────────────────────────────────
    
    def _learn_from_experiences(
        self, 
        experiences: List[Experience]
    ):
        """تحديث جدول Q من التجارب"""
        for i, exp in enumerate(experiences):
            # الحركات المتاحة في الحالة التالية
            # (تقدير: نستخدم كل الحركات الممكنة)
            next_moves = [
                Move(PlayerPosition.SOUTH, None, None)
            ]  # placeholder
            
            self.q_table.update(
                features=exp.state_features,
                move=Move(
                    PlayerPosition.SOUTH,
                    None, None
                ),  # نستخدم action_index بدلاً
                reward=exp.reward,
                next_features=exp.next_state_features,
                next_valid_moves=next_moves,
                done=exp.done
            )
    
    def _update_stats(self, result: str):
        """تحديث الإحصائيات"""
        if result.startswith('win'):
            self.stats.total_wins += 1
            if 'domino' in result:
                self.stats.total_dominos += 1
            else:
                self.stats.total_locks += 1
        elif result.startswith('loss'):
            self.stats.total_losses += 1
        else:
            self.stats.total_draws += 1
    
    # ──────────────────────────────────────────
    # التقييم
    # ──────────────────────────────────────────
    
    def _evaluate(self) -> float:
        """
        تقييم أداء النموذج الحالي
        بلعب مباريات بدون استكشاف
        """
        wins = 0
        old_epsilon = self.epsilon
        self.epsilon = 0.0  # بدون استكشاف
        
        for _ in range(self.config.eval_games):
            _, result = self._play_one_game()
            if result.startswith('win'):
                wins += 1
        
        self.epsilon = old_epsilon
        
        win_rate = wins / self.config.eval_games
        
        if win_rate > self.stats.best_win_rate:
            self.stats.best_win_rate = win_rate
            self._save_checkpoint("best")
        
        return win_rate
    
    # ──────────────────────────────────────────
    # الحفظ والتحميل
    # ──────────────────────────────────────────
    
    def _save_checkpoint(self, tag):
        """حفظ نقطة تفتيش"""
        filepath = os.path.join(
            self.config.model_dir, 
            f"domino_q_table_{tag}.pkl"
        )
        self.q_table.save(filepath)
        
        # حفظ الإحصائيات
        stats_path = os.path.join(
            self.config.log_dir,
            f"training_stats_{tag}.json"
        )
        
        stats_data = {
            'episode': self.stats.episode,
            'total_wins': self.stats.total_wins,
            'total_losses': self.stats.total_losses,
            'total_draws': self.stats.total_draws,
            'win_rate': self.stats.current_win_rate,
            'best_win_rate': self.stats.best_win_rate,
            'epsilon': self.epsilon,
            'q_table_size': len(self.q_table.table)
        }
        
        with open(stats_path, 'w') as f:
            json.dump(stats_data, f, indent=2)
    
    def load_model(self, filepath: str):
        """تحميل نموذج مدرب"""
        self.q_table.load(filepath)
        print("✅ تم تحميل النموذج المدرب")
    
    def get_trained_move(
        self,
        state: GameState,
        valid_moves: List[Move]
    ) -> Move:
        """
        الحصول على حركة من النموذج المدرب
        (للاستخدام في اللعب الفعلي)
        """
        features = FeatureExtractor.extract(state)
        return self.q_table.get_best_action(
            features, valid_moves
        )
    
    # ──────────────────────────────────────────
    # تقرير التدريب
    # ──────────────────────────────────────────
    
    def plot_training_progress(self):
        """
        رسم بياني لتقدم التدريب
        (يحتاج matplotlib)
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle(
                'تقدم تدريب الدومينو', 
                fontsize=16
            )
            
            # 1. نسبة الفوز
            if self.stats.win_rates:
                axes[0, 0].plot(
                    self.stats.win_rates, 
                    'b-', linewidth=1
                )
                axes[0, 0].set_title('نسبة الفوز')
                axes[0, 0].set_xlabel('تقييم')
                axes[0, 0].set_ylabel('Win Rate')
                axes[0, 0].axhline(
                    y=0.5, color='r', 
                    linestyle='--', alpha=0.5
                )
                axes[0, 0].set_ylim(0, 1)
            
            # 2. Epsilon
            if self.stats.epsilons:
                sample = self.stats.epsilons[::100]
                axes[0, 1].plot(
                    sample, 'g-', linewidth=1
                )
                axes[0, 1].set_title('Epsilon (استكشاف)')
                axes[0, 1].set_xlabel('حلقة (×100)')
            
            # 3. متوسط المكافآت
            if self.stats.avg_rewards:
                axes[1, 0].plot(
                    self.stats.avg_rewards, 
                    'r-', linewidth=1
                )
                axes[1, 0].set_title('متوسط المكافآت')
            
            # 4. إحصائيات
            labels = ['فوز', 'خسارة', 'تعادل']
            sizes = [
                self.stats.total_wins,
                self.stats.total_losses,
                self.stats.total_draws
            ]
            colors = ['#2ecc71', '#e74c3c', '#f39c12']
            
            if sum(sizes) > 0:
                axes[1, 1].pie(
                    sizes, labels=labels,
                    colors=colors, autopct='%1.1f%%'
                )
                axes[1, 1].set_title('توزيع النتائج')
            
            plt.tight_layout()
            
            plot_path = os.path.join(
                self.config.log_dir, 
                'training_progress.png'
            )
            plt.savefig(plot_path, dpi=150)
            plt.show()
            
            print(f"📈 تم حفظ الرسم: {plot_path}")
            
        except ImportError:
            print(
                "⚠️ matplotlib غير مثبت. "
                "ثبّته بـ: pip install matplotlib"
            )


# ──────────────────────────────────────────────
# تشغيل التدريب مباشرة
# ──────────────────────────────────────────────

if __name__ == "__main__":
    config = TrainingConfig(
        num_episodes=5000,
        eval_interval=100,
        save_interval=1000
    )
    
    trainer = DominoTrainer(config=config)
    trainer.train()
    trainer.plot_training_progress()
