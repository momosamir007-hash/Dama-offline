# tests/test_ai.py
"""
اختبارات الذكاء الاصطناعي
يتحقق من:
  - محرك الاحتمالات
  - MCTS
  - الاستراتيجيات
  - المدرب
"""

import unittest
import sys
import os
import random

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo, Move
)
from ai_brain.probability import ProbabilityEngine
from ai_brain.mcts import MCTSEngine, MCTSNode
from ai_brain.strategy import StrategyAnalyzer
from ai_brain.trainer import (
    FeatureExtractor, QTable, TrainingConfig
)
from config import GameConfig


class TestProbabilityEngine(unittest.TestCase):
    """اختبارات محرك الاحتمالات"""
    
    def setUp(self):
        self.state = GameState()
        self.state.initialize_players()
        self.state.set_my_hand([
            DominoTile(6, 6),
            DominoTile(6, 5),
            DominoTile(5, 3),
            DominoTile(4, 2),
            DominoTile(3, 1),
            DominoTile(2, 0),
            DominoTile(1, 0),
        ])
        self.engine = ProbabilityEngine(self.state)
    
    def test_unknown_tiles(self):
        """الأحجار المجهولة"""
        unknown = self.state.unknown_tiles
        self.assertEqual(len(unknown), 21)
        
        # أحجاري ليست في المجهول
        for tile in self.state.my_hand:
            self.assertNotIn(tile, unknown)
    
    def test_probabilities_sum(self):
        """مجموع الاحتمالات ≈ 1 لكل حجر"""
        probs = self.engine.calculate_tile_probabilities()
        
        unknown = list(self.state.unknown_tiles)
        
        for tile in unknown[:5]:  # نختبر أول 5
            total = sum(
                probs[pos].get(tile, 0) 
                for pos in [
                    PlayerPosition.WEST,
                    PlayerPosition.NORTH,
                    PlayerPosition.EAST
                ]
            )
            # يجب أن يكون قريب من 1
            self.assertAlmostEqual(total, 1.0, places=1)
    
    def test_passed_value_reduces_probability(self):
        """الدق يقلل الاحتمال"""
        # الخصم الغربي دق على 6
        west = self.state.players[PlayerPosition.WEST]
        west.passed_values.add(6)
        
        probs = self.engine.calculate_tile_probabilities()
        
        # احتمال أنه يملك [6|4] يجب أن يكون منخفض جداً
        tile_64 = DominoTile(6, 4)
        if tile_64 in probs[PlayerPosition.WEST]:
            prob = probs[PlayerPosition.WEST][tile_64]
            self.assertLess(prob, 0.3)
    
    def test_impossible_tiles(self):
        """الأحجار المستحيلة"""
        west = self.state.players[PlayerPosition.WEST]
        west.passed_values.add(3)
        west.passed_values.add(5)
        
        # [5|3] مستحيل عنده (دق على كليهما)
        tile = DominoTile(5, 3)
        result = self.engine._is_impossible(tile, west)
        self.assertTrue(result)
    
    def test_generate_possible_hands(self):
        """توليد أيدي محتملة"""
        samples = self.engine.generate_possible_hands(
            num_samples=10
        )
        
        self.assertGreater(len(samples), 0)
        
        for sample in samples:
            # كل خصم يجب أن يكون عنده 7 أحجار
            for pos in [
                PlayerPosition.WEST,
                PlayerPosition.NORTH,
                PlayerPosition.EAST
            ]:
                self.assertEqual(
                    len(sample[pos]),
                    self.state.players[pos].tiles_count,
                    f"{pos.name} عدد أحجار غير صحيح"
                )
            
            # لا تكرار بين اللاعبين
            all_assigned = []
            for hand in sample.values():
                all_assigned.extend(hand)
            
            self.assertEqual(
                len(all_assigned),
                len(set(all_assigned)),
                "يوجد تكرار في التوزيع"
            )


class TestMCTS(unittest.TestCase):
    """اختبارات MCTS"""
    
    def setUp(self):
        self.config = GameConfig()
        self.config.mcts_simulations = 100  # قليل للسرعة
        self.config.mcts_time_limit = 1.0
        
        self.engine = MCTSEngine(self.config)
        
        # إعداد لعبة
        self.state = GameState()
        self.state.initialize_players()
        
        # توزيع عشوائي
        all_tiles = list(self.state.ALL_TILES)
        random.seed(42)
        random.shuffle(all_tiles)
        
        for i, pos in enumerate(PlayerPosition):
            hand = all_tiles[i * 7:(i + 1) * 7]
            self.state.players[pos].hand = hand
            self.state.players[pos].tiles_count = len(hand)
    
    def test_find_best_move(self):
        """إيجاد أفضل حركة"""
        best_move, analysis = self.engine.find_best_move(
            self.state
        )
        
        # يجب أن يعيد حركة
        self.assertIsNotNone(best_move)
        self.assertIsInstance(best_move, Move)
        
        # التحليل يجب أن يحتوي على المعلومات
        self.assertIn('total_simulations', analysis)
        self.assertIn('moves_analysis', analysis)
        self.assertGreater(
            analysis['total_simulations'], 0
        )
    
    def test_move_is_valid(self):
        """الحركة المقترحة يجب أن تكون صحيحة"""
        best_move, _ = self.engine.find_best_move(
            self.state
        )
        
        valid_moves = self.state.get_valid_moves(
            self.state.current_turn
        )
        
        # الحركة المقترحة يجب أن تكون من الحركات المتاحة
        move_found = False
        for vm in valid_moves:
            if (
                vm.tile == best_move.tile and 
                vm.direction == best_move.direction
            ):
                move_found = True
                break
        
        self.assertTrue(
            move_found,
            f"الحركة {best_move} ليست من الحركات المتاحة"
        )
    
    def test_ucb1(self):
        """UCB1 formula"""
        parent = MCTSNode(state=self.state.clone())
        parent.visits = 100
        
        child = MCTSNode(
            state=self.state.clone(),
            parent=parent
        )
        child.visits = 10
        child.wins = 7
        
        ucb = child.ucb1(exploration=1.414)
        
        # يجب أن يكون أكبر من معدل الفوز
        self.assertGreater(ucb, 0.7)
    
    def test_analysis_has_win_rates(self):
        """التحليل يحتوي على نسب الفوز"""
        _, analysis = self.engine.find_best_move(
            self.state
        )
        
        for ma in analysis['moves_analysis']:
            self.assertIn('win_rate', ma)
            self.assertIn('confidence', ma)
            self.assertIn('visits', ma)


class TestStrategy(unittest.TestCase):
    """اختبارات الاستراتيجيات"""
    
    def setUp(self):
        self.state = GameState()
        self.state.initialize_players()
        self.state.set_my_hand([
            DominoTile(6, 6),
            DominoTile(6, 5),
            DominoTile(6, 3),
            DominoTile(6, 1),
            DominoTile(5, 2),
            DominoTile(3, 0),
            DominoTile(1, 0),
        ])
        
        self.analyzer = StrategyAnalyzer(self.state)
    
    def test_analyze_move(self):
        """تحليل حركة"""
        move = Move(
            PlayerPosition.SOUTH,
            DominoTile(6, 6),
            Direction.LEFT
        )
        
        analysis = self.analyzer.analyze_move(move)
        
        self.assertIn('move', analysis)
        self.assertIn('reasons', analysis)
        self.assertIn('score', analysis)
    
    def test_heavy_tile_detection(self):
        """اكتشاف الأحجار الثقيلة"""
        move = Move(
            PlayerPosition.SOUTH,
            DominoTile(6, 6),  # 12 نقطة
            Direction.LEFT
        )
        
        analysis = self.analyzer.analyze_move(move)
        
        # يجب أن يذكر أنه حجر ثقيل
        reasons_text = " ".join(analysis.get('reasons', []))
        has_weight_mention = (
            'ثقيل' in reasons_text or 
            'دبل' in reasons_text or
            analysis['score'] > 0
        )
        self.assertTrue(has_weight_mention)
    
    def test_pass_analysis(self):
        """تحليل الدق"""
        move = Move(
            PlayerPosition.SOUTH, None, None
        )
        
        analysis = self.analyzer.analyze_move(move)
        self.assertEqual(analysis['type'], 'pass')


class TestFeatureExtractor(unittest.TestCase):
    """اختبارات استخراج الميزات"""
    
    def setUp(self):
        self.state = GameState()
        self.state.initialize_players()
        self.state.set_my_hand([
            DominoTile(6, 6),
            DominoTile(5, 3),
            DominoTile(4, 2),
            DominoTile(3, 1),
            DominoTile(2, 0),
            DominoTile(1, 0),
            DominoTile(6, 4),
        ])
    
    def test_feature_size(self):
        """حجم شعاع الميزات"""
        features = FeatureExtractor.extract(self.state)
        expected_size = FeatureExtractor.feature_size()
        
        self.assertEqual(len(features), expected_size)
    
    def test_features_are_normalized(self):
        """القيم مطبّعة (بين -1 و 2)"""
        features = FeatureExtractor.extract(self.state)
        
        self.assertTrue(
            all(-1.5 <= f <= 2.0 for f in features),
            f"قيم خارج النطاق: "
            f"min={min(features)}, max={max(features)}"
        )
    
    def test_my_tiles_encoded(self):
        """أحجاري مشفّرة بشكل صحيح"""
        features = FeatureExtractor.extract(self.state)
        
        # أول 28 قيمة = أحجاري (0 أو 1)
        my_tiles_features = features[:28]
        
        # يجب أن يكون 7 منها = 1
        num_ones = sum(
            1 for f in my_tiles_features if f == 1.0
        )
        self.assertEqual(num_ones, 7)
    
    def test_different_states_different_features(self):
        """حالات مختلفة = ميزات مختلفة"""
        f1 = FeatureExtractor.extract(self.state)
        
        state2 = self.state.clone()
        state2.set_my_hand([
            DominoTile(0, 0),
            DominoTile(1, 1),
        ])
        
        f2 = FeatureExtractor.extract(state2)
        
        # يجب أن تكون مختلفة
        self.assertFalse(
            all(a == b for a, b in zip(f1, f2))
        )


class TestQTable(unittest.TestCase):
    """اختبارات جدول Q"""
    
    def setUp(self):
        self.q_table = QTable(
            learning_rate=0.1,
            discount=0.95
        )
        
        import numpy as np
        self.dummy_features = np.random.rand(80).astype(
            np.float32
        )
        self.dummy_move = Move(
            PlayerPosition.SOUTH,
            DominoTile(6, 5),
            Direction.LEFT
        )
    
    def test_default_value(self):
        """القيمة الافتراضية = 0"""
        value = self.q_table.get_value(
            self.dummy_features, self.dummy_move
        )
        self.assertEqual(value, 0.0)
    
    def test_update(self):
        """تحديث القيمة"""
        self.q_table.update(
            features=self.dummy_features,
            move=self.dummy_move,
            reward=10.0,
            next_features=None,
            next_valid_moves=[],
            done=True
        )
        
        value = self.q_table.get_value(
            self.dummy_features, self.dummy_move
        )
        
        # يجب أن تكون > 0 بعد مكافأة إيجابية
        self.assertGreater(value, 0.0)
    
    def test_best_action(self):
        """أفضل حركة"""
        move1 = Move(
            PlayerPosition.SOUTH,
            DominoTile(6, 5),
            Direction.LEFT
        )
        move2 = Move(
            PlayerPosition.SOUTH,
            DominoTile(3, 1),
            Direction.RIGHT
        )
        
        # نعطي move1 مكافأة أعلى
        self.q_table.update(
            self.dummy_features, move1,
            reward=10.0, next_features=None,
            next_valid_moves=[], done=True
        )
        self.q_table.update(
            self.dummy_features, move2,
            reward=2.0, next_features=None,
            next_valid_moves=[], done=True
        )
        
        best = self.q_table.get_best_action(
            self.dummy_features, [move1, move2]
        )
        
        self.assertEqual(best.tile, move1.tile)
    
    def test_save_load(self):
        """حفظ وتحميل"""
        import tempfile
        
        # تحديث بعض القيم
        self.q_table.update(
            self.dummy_features, self.dummy_move,
            reward=5.0, next_features=None,
            next_valid_moves=[], done=True
        )
        
        # حفظ
        with tempfile.NamedTemporaryFile(
            suffix='.pkl', delete=False
        ) as f:
            filepath = f.name
        
        self.q_table.save(filepath)
        
        # تحميل في جدول جديد
        new_table = QTable()
        new_table.load(filepath)
        
        # التحقق
        value = new_table.get_value(
            self.dummy_features, self.dummy_move
        )
        self.assertGreater(value, 0.0)
        
        # تنظيف
        os.unlink(filepath)


if __name__ == '__main__':
    unittest.main(verbosity=2)
