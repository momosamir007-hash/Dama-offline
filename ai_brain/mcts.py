# ai_brain/mcts.py
"""
Monte Carlo Tree Search - البحث في شجرة مونت كارلو
القلب الذكي للمساعد
"""
import math
import time
import random
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from game_engine.game_state import (
    GameState, Move, PlayerPosition
)
from game_engine.domino_board import DominoTile, Direction
from ai_brain.probability import ProbabilityEngine
from config import GameConfig


@dataclass
class MCTSNode:
    """عقدة في شجرة البحث"""
    state: GameState
    move: Optional[Move] = None           # الحركة التي أدت لهذه العقدة
    parent: Optional['MCTSNode'] = None
    children: List['MCTSNode'] = field(default_factory=list)
    
    wins: float = 0.0
    visits: int = 0
    untried_moves: List[Move] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.untried_moves and not self.state.is_game_over:
            self.untried_moves = self.state.get_valid_moves(
                self.state.current_turn
            )
    
    @property
    def is_fully_expanded(self) -> bool:
        return len(self.untried_moves) == 0
    
    @property
    def is_terminal(self) -> bool:
        return self.state.is_game_over
    
    def ucb1(self, exploration: float = 1.414) -> float:
        """
        Upper Confidence Bound formula
        يوازن بين:
        - الاستغلال (exploitation): الحركات اللي نجحت
        - الاستكشاف (exploration): الحركات اللي ما جربناها كثير
        """
        if self.visits == 0:
            return float('inf')
        
        exploitation = self.wins / self.visits
        exploration_term = exploration * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        
        return exploitation + exploration_term
    
    def best_child(self, exploration: float = 1.414) -> 'MCTSNode':
        """أفضل عقدة ابن حسب UCB1"""
        return max(
            self.children, 
            key=lambda c: c.ucb1(exploration)
        )
    
    def best_move_child(self) -> 'MCTSNode':
        """أفضل حركة (أكثر زيارات = أكثر ثقة)"""
        return max(
            self.children, 
            key=lambda c: c.visits
        )


class MCTSEngine:
    """
    محرك البحث في شجرة مونت كارلو
    
    الخوارزمية:
    1. Selection: اختر أفضل مسار في الشجرة
    2. Expansion: وسّع الشجرة بعقدة جديدة
    3. Simulation: محاكاة عشوائية حتى نهاية اللعبة
    4. Backpropagation: حدّث النتائج للأعلى
    """
    
    def __init__(self, config: GameConfig = None):
        self.config = config or GameConfig()
        self.probability_engine: Optional[ProbabilityEngine] = None
    
    def find_best_move(
        self, 
        game_state: GameState,
        time_limit: float = None,
        num_simulations: int = None
    ) -> Tuple[Move, Dict]:
        """
        إيجاد أفضل حركة
        
        Returns:
            (أفضل حركة, تفاصيل التحليل)
        """
        time_limit = time_limit or self.config.mcts_time_limit
        num_simulations = (
            num_simulations or self.config.mcts_simulations
        )
        
        self.probability_engine = ProbabilityEngine(game_state)
        
        # إنشاء جذر الشجرة
        root = MCTSNode(state=game_state.clone())
        
        start_time = time.time()
        simulations_done = 0
        
        while (
            simulations_done < num_simulations and 
            time.time() - start_time < time_limit
        ):
            # 1. Selection
            node = self._select(root)
            
            # 2. Expansion
            if not node.is_terminal and not node.is_fully_expanded:
                node = self._expand(node)
            
            # 3. Simulation
            result = self._simulate(node)
            
            # 4. Backpropagation
            self._backpropagate(node, result)
            
            simulations_done += 1
        
        # اختيار أفضل حركة
        best_child = root.best_move_child()
        
        # تجميع التحليل
        analysis = self._build_analysis(
            root, simulations_done, time.time() - start_time
        )
        
        return best_child.move, analysis
    
    def _select(self, node: MCTSNode) -> MCTSNode:
        """
        Selection Phase
        ننزل في الشجرة باختيار أفضل ابن حتى نصل لعقدة
        غير مكتملة التوسع أو نهائية
        """
        current = node
        while (
            not current.is_terminal and 
            current.is_fully_expanded
        ):
            current = current.best_child(
                self.config.mcts_exploration
            )
        return current
    
    def _expand(self, node: MCTSNode) -> MCTSNode:
        """
        Expansion Phase
        نضيف عقدة ابن جديدة بحركة لم نجربها
        """
        # اختر حركة عشوائية من الحركات غير المجربة
        move = node.untried_moves.pop(
            random.randint(0, len(node.untried_moves) - 1)
        )
        
        # أنشئ حالة جديدة
        new_state = node.state.clone()
        new_state.apply_move(move)
        
        # أنشئ عقدة ابن
        child = MCTSNode(
            state=new_state,
            move=move,
            parent=node
        )
        
        node.children.append(child)
        return child
    
    def _simulate(self, node: MCTSNode) -> float:
        """
        Simulation Phase (Rollout)
        نلعب عشوائياً حتى نهاية اللعبة
        
        هنا نستخدم محرك الاحتمالات لتوزيع 
        الأحجار المجهولة على الخصوم
        """
        sim_state = node.state.clone()
        
        # توزيع الأحجار المجهولة على الخصوم
        self._assign_unknown_tiles(sim_state)
        
        # لعب عشوائي حتى النهاية
        max_moves = 100  # حماية من الحلقة اللانهائية
        moves_played = 0
        
        while (
            not sim_state.is_game_over and 
            moves_played < max_moves
        ):
            valid_moves = sim_state.get_valid_moves(
                sim_state.current_turn
            )
            
            # اختيار عشوائي مع تفضيل ذكي
            move = self._smart_random_move(
                valid_moves, sim_state
            )
            
            sim_state.apply_move(move)
            moves_played += 1
        
        # تقييم النتيجة
        return self._evaluate_result(sim_state)
    
    def _assign_unknown_tiles(self, state: GameState):
        """
        توزيع الأحجار المجهولة على الخصوم
        مع مراعاة قيود الـ "دق"
        """
        samples = self.probability_engine.generate_possible_hands(
            num_samples=1
        )
        
        if samples:
            for pos, hand in samples[0].items():
                state.players[pos].hand = hand
    
    def _smart_random_move(
        self, 
        moves: List[Move], 
        state: GameState
    ) -> Move:
        """
        اختيار شبه عشوائي مع بعض الذكاء
        (يفضل الدبل والأحجار الثقيلة)
        """
        if len(moves) == 1:
            return moves[0]
        
        # فصل الحركات الحقيقية عن الـ "دق"
        real_moves = [m for m in moves if not m.is_pass]
        if not real_moves:
            return moves[0]
        
        # وزن الحركات
        weights = []
        for move in real_moves:
            weight = 1.0
            
            # تفضيل الدبل
            if move.tile.is_double:
                weight *= 2.0
            
            # تفضيل الأحجار الثقيلة (تخلص منها بسرعة)
            weight *= (1.0 + move.tile.total * 0.1)
            
            weights.append(weight)
        
        # اختيار موزون
        total_weight = sum(weights)
        probs = [w / total_weight for w in weights]
        
        import numpy as np
        idx = np.random.choice(len(real_moves), p=probs)
        return real_moves[idx]
    
    def _evaluate_result(self, state: GameState) -> float:
        """
        تقييم نتيجة المحاكاة
        1.0 = فوز كامل
        0.0 = خسارة كاملة
        0.5 = تعادل
        """
        if state.winner is None:
            return 0.5
        
        # أنا أو شريكي فزنا
        if state.winner in (
            PlayerPosition.SOUTH, 
            PlayerPosition.NORTH
        ):
            return 1.0
        
        return 0.0
    
    def _backpropagate(self, node: MCTSNode, result: float):
        """
        Backpropagation Phase
        نحدّث النتائج من العقدة الحالية حتى الجذر
        """
        current = node
        while current is not None:
            current.visits += 1
            
            # لو دور الخصم = نعكس النتيجة
            if current.state.current_turn in (
                PlayerPosition.WEST, 
                PlayerPosition.EAST
            ):
                current.wins += (1.0 - result)
            else:
                current.wins += result
            
            current = current.parent
    
    def _build_analysis(
        self, 
        root: MCTSNode,
        simulations: int,
        elapsed: float
    ) -> Dict:
        """
        بناء تقرير التحليل
        """
        analysis = {
            'total_simulations': simulations,
            'time_elapsed': f"{elapsed:.2f}s",
            'moves_analysis': []
        }
        
        # ترتيب الحركات حسب عدد الزيارات
        sorted_children = sorted(
            root.children, 
            key=lambda c: c.visits, 
            reverse=True
        )
        
        for child in sorted_children:
            win_rate = (
                child.wins / child.visits 
                if child.visits > 0 else 0
            )
            
            analysis['moves_analysis'].append({
                'move': str(child.move),
                'visits': child.visits,
                'win_rate': f"{win_rate:.1%}",
                'confidence': self._confidence_level(win_rate)
            })
        
        return analysis
    
    def _confidence_level(self, win_rate: float) -> str:
        """مستوى الثقة"""
        if win_rate >= 0.75:
            return "🟢 ممتاز"
        elif win_rate >= 0.55:
            return "🟡 جيد"
        elif win_rate >= 0.40:
            return "🟠 متوسط"
        else:
            return "🔴 ضعيف"
