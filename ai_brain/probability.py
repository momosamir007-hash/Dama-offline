# ai_brain/probability.py
"""
محرك الاحتمالات - يحسب احتمال امتلاك كل خصم لكل حجر
بناءً على:
  1. الأحجار المعروفة (يدي + الطاولة)
  2. الأرقام اللي دق عليها كل خصم
  3. الأحجار اللي لعبها كل خصم
  4. عدد الأحجار المتبقية عند كل خصم
"""
from typing import Dict, Set, List, Tuple
from collections import defaultdict
import numpy as np

from game_engine.domino_board import DominoTile
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo
)


class ProbabilityEngine:
    """
    محرك احتمالات بايزي لتوقع أحجار الخصوم
    """
    
    def __init__(self, game_state: GameState):
        self.state = game_state
        self._cache = {}
    
    def calculate_tile_probabilities(
        self
    ) -> Dict[PlayerPosition, Dict[DominoTile, float]]:
        """
        لكل خصم، احتمال امتلاكه لكل حجر مجهول
        
        Returns:
            {
                PlayerPosition.WEST: {
                    DominoTile(6,5): 0.42,
                    DominoTile(3,1): 0.15,
                    ...
                },
                ...
            }
        """
        unknown_tiles = list(self.state.unknown_tiles)
        opponents = [
            PlayerPosition.WEST, 
            PlayerPosition.NORTH, 
            PlayerPosition.EAST
        ]
        
        probabilities = {
            pos: {} for pos in opponents
        }
        
        for tile in unknown_tiles:
            for pos in opponents:
                prob = self._tile_probability(tile, pos)
                probabilities[pos][tile] = prob
        
        # تطبيع الاحتمالات
        probabilities = self._normalize(
            probabilities, unknown_tiles, opponents
        )
        
        return probabilities
    
    def _tile_probability(
        self, 
        tile: DominoTile, 
        player: PlayerPosition
    ) -> float:
        """
        احتمال أن هذا اللاعب يملك هذا الحجر
        """
        player_info = self.state.players[player]
        
        # لو اللاعب ما عنده أحجار
        if player_info.tiles_count <= 0:
            return 0.0
        
        # لو اللاعب دق على أحد أرقام الحجر
        # (يعني ما عنده هالرقم)
        if self._is_impossible(tile, player_info):
            return 0.0
        
        # الاحتمال الأساسي (توزيع متساوي)
        total_unknown = len(self.state.unknown_tiles)
        total_opponent_tiles = sum(
            self.state.players[p].tiles_count 
            for p in [
                PlayerPosition.WEST, 
                PlayerPosition.NORTH, 
                PlayerPosition.EAST
            ]
        )
        
        if total_unknown == 0:
            return 0.0
        
        base_prob = player_info.tiles_count / total_unknown
        
        # تعديل بناءً على سلوك اللاعب
        behavior_factor = self._behavior_adjustment(
            tile, player_info
        )
        
        return base_prob * behavior_factor
    
    def _is_impossible(
        self, 
        tile: DominoTile, 
        player: PlayerInfo
    ) -> bool:
        """
        هل من المستحيل أن يملك اللاعب هذا الحجر؟
        
        مستحيل إذا:
        - دق على كلا رقمي الحجر
        - أو إذا كان الحجر دبل ودق على رقمه
        """
        if tile.is_double:
            # دبل: يكفي أنه دق على الرقم مرة
            return tile.high in player.passed_values
        else:
            # عادي: لازم يكون دق على كلا الرقمين
            # ليكون مستحيل
            # لكن في الواقع، لو دق على رقم واحد فقط
            # الحجر لا يزال ممكن (الطرف الثاني مفتوح ما كان موجود)
            # 
            # القاعدة الدقيقة:
            # لو الطاولة كان طرفها الأيسر 5 والأيمن 3
            # واللاعب دق = ما عنده 5 ولا 3
            # فأي حجر فيه 5 أو 3 بس ما عنده
            # لكن حجر [5|2] ما يقدر يلعبه لأنه ما فيه طرف 2
            # 
            # الأصح: لو دق لما كان الطرف فيه رقم X
            # فما عنده أي حجر فيه X
            
            # نتحقق: هل كلا رقمي الحجر "مدقوق" عليهم؟
            both_passed = (
                tile.high in player.passed_values and 
                tile.low in player.passed_values
            )
            
            # أو: هل الحجر فيه رقم واحد بس من المدقوق
            # وهذا الرقم هو الوحيد اللي يخلي الحجر يتلعب
            # هذا تحليل أعقد - نبسطه:
            
            # لو دق على أي رقم من أرقام الحجر
            # احتمال أنه عنده ينخفض لكن ما يصبح صفر
            # إلا لو دق على كليهما
            
            return both_passed
    
    def _behavior_adjustment(
        self, 
        tile: DominoTile, 
        player: PlayerInfo
    ) -> float:
        """
        تعديل الاحتمال بناءً على سلوك اللعب
        """
        factor = 1.0
        
        # لو لعب أحجار كثيرة من رقم معين
        # احتمال أنه لا يزال يملك من نفس الرقم يقل
        played_values = defaultdict(int)
        for played_tile in player.played_tiles:
            played_values[played_tile.high] += 1
            played_values[played_tile.low] += 1
        
        for val in tile.pip_values:
            times_played = played_values.get(val, 0)
            # كل ما لعب أكثر من رقم، احتمال أنه عنده المزيد يقل
            factor *= (1.0 / (1.0 + times_played * 0.3))
        
        # لو دق على أحد الأرقام (مش كليهما)
        for val in tile.pip_values:
            if val in player.passed_values:
                factor *= 0.05  # شبه مستحيل
        
        return factor
    
    def _normalize(
        self,
        probabilities: Dict,
        unknown_tiles: List[DominoTile],
        opponents: List[PlayerPosition]
    ) -> Dict:
        """
        تطبيع الاحتمالات بحيث:
        - مجموع احتمالات كل حجر عبر كل الخصوم ≈ 1
        - مجموع أحجار كل خصم ≈ عدد أحجاره
        """
        for tile in unknown_tiles:
            total = sum(
                probabilities[pos].get(tile, 0) 
                for pos in opponents
            )
            if total > 0:
                for pos in opponents:
                    if tile in probabilities[pos]:
                        probabilities[pos][tile] /= total
        
        return probabilities
    
    def generate_possible_hands(
        self, 
        num_samples: int = 100
    ) -> List[Dict[PlayerPosition, List[DominoTile]]]:
        """
        توليد توزيعات محتملة لأحجار الخصوم
        تُستخدم في محاكاة مونت كارلو
        
        تُنشئ num_samples سيناريو محتمل لتوزيع الأحجار
        """
        unknown = list(self.state.unknown_tiles)
        opponents = [
            PlayerPosition.WEST, 
            PlayerPosition.NORTH, 
            PlayerPosition.EAST
        ]
        
        hand_sizes = {
            pos: self.state.players[pos].tiles_count 
            for pos in opponents
        }
        
        # الأحجار المستحيلة لكل خصم
        impossible = {pos: set() for pos in opponents}
        for pos in opponents:
            player = self.state.players[pos]
            for tile in unknown:
                if self._is_impossible(tile, player):
                    impossible[pos].add(tile)
        
        samples = []
        
        for _ in range(num_samples):
            sample = self._generate_one_hand(
                unknown, opponents, hand_sizes, impossible
            )
            if sample is not None:
                samples.append(sample)
        
        return samples
    
    def _generate_one_hand(
        self,
        unknown: List[DominoTile],
        opponents: List[PlayerPosition],
        hand_sizes: Dict[PlayerPosition, int],
        impossible: Dict[PlayerPosition, Set[DominoTile]]
    ) -> Dict[PlayerPosition, List[DominoTile]] | None:
        """
        توليد توزيع واحد محتمل مع مراعاة القيود
        باستخدام Constraint-Aware Sampling
        """
        available = list(unknown)
        np.random.shuffle(available)
        
        hands = {pos: [] for pos in opponents}
        used = set()
        
        # نوزع حسب الأولوية (اللاعب بقيود أكثر أولاً)
        sorted_opponents = sorted(
            opponents, 
            key=lambda p: len(impossible[p]), 
            reverse=True
        )
        
        for pos in sorted_opponents:
            needed = hand_sizes[pos]
            eligible = [
                t for t in available 
                if t not in used and t not in impossible[pos]
            ]
            
            if len(eligible) < needed:
                return None  # توزيع مستحيل
            
            chosen = list(
                np.random.choice(
                    len(eligible), needed, replace=False
                )
            )
            
            for idx in chosen:
                tile = eligible[idx]
                hands[pos].append(tile)
                used.add(tile)
        
        return hands
    
    def display_probabilities(self):
        """عرض الاحتمالات بشكل مقروء"""
        probs = self.calculate_tile_probabilities()
        
        print("\n" + "=" * 60)
        print("تحليل احتمالات أحجار الخصوم")
        print("=" * 60)
        
        for pos in [
            PlayerPosition.WEST, 
            PlayerPosition.NORTH, 
            PlayerPosition.EAST
        ]:
            print(f"\n{'─' * 40}")
            name_map = {
                PlayerPosition.WEST: "اللاعب الغربي (يمينك)",
                PlayerPosition.NORTH: "الشريك (قدامك)",
                PlayerPosition.EAST: "اللاعب الشرقي (يسارك)"
            }
            print(f"  {name_map[pos]}")
            print(f"  أحجار متبقية: "
                  f"{self.state.players[pos].tiles_count}")
            
            # ترتيب حسب الاحتمال
            sorted_tiles = sorted(
                probs[pos].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            for tile, prob in sorted_tiles[:10]:
                bar = "█" * int(prob * 30)
                print(f"  {tile}: {prob:.1%} {bar}")
