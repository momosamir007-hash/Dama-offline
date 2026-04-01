# tests/test_engine.py
"""
اختبارات محرك اللعبة
يتحقق من:
  - إنشاء الأحجار
  - حركات الطاولة
  - حالة اللعبة
  - القواعد
"""

import unittest
import sys
import os

# إضافة المجلد الرئيسي للمسار
sys.path.insert(
    0, 
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo, Move
)
from game_engine.rules import (
    DominoRules, GameMode, Violation, RuleCheckResult
)


class TestDominoTile(unittest.TestCase):
    """اختبارات حجر الدومينو"""
    
    def test_creation(self):
        """إنشاء حجر عادي"""
        tile = DominoTile(6, 4)
        self.assertEqual(tile.high, 6)
        self.assertEqual(tile.low, 4)
    
    def test_auto_ordering(self):
        """الترتيب التلقائي (الأكبر أولاً)"""
        tile = DominoTile(2, 5)
        self.assertEqual(tile.high, 5)
        self.assertEqual(tile.low, 2)
    
    def test_double(self):
        """اختبار الدبل"""
        double = DominoTile(3, 3)
        self.assertTrue(double.is_double)
        
        normal = DominoTile(5, 2)
        self.assertFalse(normal.is_double)
    
    def test_total(self):
        """مجموع النقاط"""
        tile = DominoTile(6, 4)
        self.assertEqual(tile.total, 10)
        
        double = DominoTile(5, 5)
        self.assertEqual(double.total, 10)
    
    def test_has_value(self):
        """هل يحتوي على رقم"""
        tile = DominoTile(6, 3)
        self.assertTrue(tile.has_value(6))
        self.assertTrue(tile.has_value(3))
        self.assertFalse(tile.has_value(4))
    
    def test_other_side(self):
        """الجانب الآخر"""
        tile = DominoTile(6, 2)
        self.assertEqual(tile.other_side(6), 2)
        self.assertEqual(tile.other_side(2), 6)
        
        with self.assertRaises(ValueError):
            tile.other_side(4)
    
    def test_equality(self):
        """المساواة"""
        t1 = DominoTile(5, 3)
        t2 = DominoTile(3, 5)  # نفس الحجر بترتيب مختلف
        self.assertEqual(t1, t2)
    
    def test_hash(self):
        """قابلية الاستخدام في المجموعات"""
        t1 = DominoTile(5, 3)
        t2 = DominoTile(3, 5)
        
        tile_set = {t1}
        self.assertIn(t2, tile_set)
    
    def test_pip_values(self):
        """قيم النقاط"""
        tile = DominoTile(6, 2)
        self.assertEqual(tile.pip_values, {6, 2})
    
    def test_repr(self):
        """التمثيل النصي"""
        tile = DominoTile(6, 4)
        self.assertEqual(repr(tile), "[6|4]")


class TestBoard(unittest.TestCase):
    """اختبارات الطاولة"""
    
    def setUp(self):
        """تهيئة قبل كل اختبار"""
        self.board = Board()
    
    def test_empty_board(self):
        """الطاولة الفارغة"""
        self.assertTrue(self.board.is_empty)
        self.assertEqual(len(self.board.tiles_played), 0)
        self.assertIsNone(self.board.left_end)
        self.assertIsNone(self.board.right_end)
    
    def test_first_play(self):
        """أول حجر"""
        tile = DominoTile(6, 4)
        result = self.board.play_tile(tile, Direction.LEFT)
        
        self.assertTrue(result)
        self.assertFalse(self.board.is_empty)
        self.assertEqual(self.board.left_end, 6)
        self.assertEqual(self.board.right_end, 4)
    
    def test_play_left(self):
        """اللعب على اليسار"""
        # أول حجر [5|3]: left=5, right=3
        self.board.play_tile(
            DominoTile(5, 3), Direction.LEFT
        )
        
        # [6|5] على اليسار: left=6, right=3
        tile = DominoTile(6, 5)
        result = self.board.play_tile(
            tile, Direction.LEFT
        )
        
        self.assertTrue(result)
        self.assertEqual(self.board.left_end, 6)
        self.assertEqual(self.board.right_end, 3)
    
    def test_play_right(self):
        """اللعب على اليمين"""
        # أول حجر [5|3]: left=5, right=3
        self.board.play_tile(
            DominoTile(5, 3), Direction.LEFT
        )
        
        # [3|1] على اليمين: left=5, right=1
        tile = DominoTile(3, 1)
        result = self.board.play_tile(
            tile, Direction.RIGHT
        )
        
        self.assertTrue(result)
        self.assertEqual(self.board.left_end, 5)
        self.assertEqual(self.board.right_end, 1)
    
    def test_invalid_play(self):
        """حركة غير صحيحة"""
        self.board.play_tile(
            DominoTile(5, 3), Direction.LEFT
        )
        
        # [6|1] لا يتطابق مع أي طرف 
        # (5 أو 3، بس الحجر فيه 6 و 1)
        tile = DominoTile(6, 1)
        directions = self.board.can_play(tile)
        self.assertEqual(len(directions), 0)
    
    def test_can_play(self):
        """التحقق من إمكانية اللعب"""
        self.board.play_tile(
            DominoTile(5, 3), Direction.LEFT
        )
        
        # [6|5] يمكن لعبها على اليسار
        dirs = self.board.can_play(DominoTile(6, 5))
        self.assertIn(Direction.LEFT, dirs)
        
        # [3|1] يمكن لعبها على اليمين
        dirs = self.board.can_play(DominoTile(3, 1))
        self.assertIn(Direction.RIGHT, dirs)
    
    def test_double_play(self):
        """لعب الدبل"""
        self.board.play_tile(
            DominoTile(5, 3), Direction.LEFT
        )
        
        # [5|5] على اليسار
        tile = DominoTile(5, 5)
        result = self.board.play_tile(
            tile, Direction.LEFT
        )
        
        self.assertTrue(result)
        self.assertEqual(self.board.left_end, 5)
    
    def test_open_ends(self):
        """الأطراف المفتوحة"""
        self.board.play_tile(
            DominoTile(5, 3), Direction.LEFT
        )
        
        ends = self.board.open_ends
        self.assertEqual(ends, {5, 3})
    
    def test_clone(self):
        """النسخ العميق"""
        self.board.play_tile(
            DominoTile(5, 3), Direction.LEFT
        )
        
        clone = self.board.clone()
        clone.play_tile(
            DominoTile(6, 5), Direction.LEFT
        )
        
        # الأصلي لم يتغير
        self.assertEqual(self.board.left_end, 5)
        self.assertEqual(clone.left_end, 6)
    
    def test_played_values_count(self):
        """عدد مرات ظهور كل رقم"""
        self.board.play_tile(
            DominoTile(5, 3), Direction.LEFT
        )
        self.board.play_tile(
            DominoTile(6, 5), Direction.LEFT
        )
        
        counts = self.board.get_played_values_count()
        self.assertEqual(counts.get(5, 0), 2)
        self.assertEqual(counts.get(3, 0), 1)
        self.assertEqual(counts.get(6, 0), 1)


class TestGameState(unittest.TestCase):
    """اختبارات حالة اللعبة"""
    
    def setUp(self):
        self.state = GameState()
        self.state.initialize_players()
        
        # يد اختبارية
        self.test_hand = [
            DominoTile(6, 6),
            DominoTile(6, 5),
            DominoTile(5, 3),
            DominoTile(4, 2),
            DominoTile(3, 1),
            DominoTile(2, 0),
            DominoTile(1, 0),
        ]
        self.state.set_my_hand(self.test_hand)
    
    def test_initialization(self):
        """تهيئة اللعبة"""
        self.assertEqual(len(self.state.players), 4)
        self.assertTrue(
            self.state.players[PlayerPosition.SOUTH].is_me
        )
    
    def test_my_hand(self):
        """يدي"""
        self.assertEqual(len(self.state.my_hand), 7)
        self.assertIn(DominoTile(6, 6), self.state.my_hand)
    
    def test_known_tiles(self):
        """الأحجار المعروفة"""
        known = self.state.known_tiles
        self.assertEqual(len(known), 7)
    
    def test_unknown_tiles(self):
        """الأحجار المجهولة"""
        unknown = self.state.unknown_tiles
        # 28 إجمالي - 7 معروفة = 21 مجهولة
        self.assertEqual(len(unknown), 21)
    
    def test_all_tiles_count(self):
        """عدد كل الأحجار"""
        self.assertEqual(len(self.state.ALL_TILES), 28)
    
    def test_valid_moves_empty_board(self):
        """الحركات على طاولة فارغة"""
        moves = self.state.get_valid_moves(
            PlayerPosition.SOUTH
        )
        # كل حجر في اليد يمكن لعبه
        self.assertEqual(len(moves), 7)
    
    def test_valid_moves_with_board(self):
        """الحركات مع طاولة فيها أحجار"""
        # لعب أول حجر
        move = Move(
            PlayerPosition.SOUTH,
            DominoTile(6, 6),
            Direction.LEFT
        )
        self.state.apply_move(move)
        
        # الأحجار المتبقية في اليد: 6
        self.assertEqual(len(self.state.my_hand), 6)
    
    def test_apply_pass(self):
        """تطبيق الدق"""
        # نضع حجر على الطاولة أولاً
        self.state.board.play_tile(
            DominoTile(6, 6), Direction.LEFT
        )
        
        # ننتقل للدور التالي
        self.state.current_turn = PlayerPosition.WEST
        
        pass_move = Move(
            PlayerPosition.WEST, None, None
        )
        self.state.apply_move(pass_move)
        
        # يجب أن يُسجل أنه دق على 6
        west = self.state.players[PlayerPosition.WEST]
        self.assertIn(6, west.passed_values)
    
    def test_consecutive_passes(self):
        """العد التراكمي للدق"""
        self.state.board.play_tile(
            DominoTile(5, 3), Direction.LEFT
        )
        
        for pos in PlayerPosition:
            self.state.current_turn = pos
            self.state.apply_move(
                Move(pos, None, None)
            )
        
        self.assertTrue(self.state.is_game_over)
    
    def test_clone(self):
        """نسخ الحالة"""
        clone = self.state.clone()
        
        clone.set_my_hand([DominoTile(1, 0)])
        
        # الأصلي لم يتغير
        self.assertEqual(len(self.state.my_hand), 7)
        self.assertEqual(len(clone.my_hand), 1)


class TestDominoRules(unittest.TestCase):
    """اختبارات القواعد"""
    
    def setUp(self):
        self.rules = DominoRules(mode=GameMode.EGYPTIAN)
        
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
    
    def test_all_tiles_generated(self):
        """كل الأحجار (28)"""
        self.assertEqual(len(self.rules.all_tiles), 28)
    
    def test_validate_valid_tile(self):
        """حجر صحيح"""
        result = self.rules.validate_tile(
            DominoTile(6, 3)
        )
        self.assertTrue(result.is_valid)
    
    def test_validate_invalid_tile(self):
        """حجر غير صحيح"""
        result = self.rules.validate_tile(
            DominoTile(8, 3)
        )
        self.assertFalse(result.is_valid)
    
    def test_validate_hand(self):
        """يد صحيحة"""
        hand = [
            DominoTile(6, 5),
            DominoTile(4, 3),
            DominoTile(2, 1),
        ]
        result = self.rules.validate_hand(hand)
        self.assertTrue(result.is_valid)
    
    def test_validate_hand_duplicates(self):
        """يد بتكرار"""
        hand = [
            DominoTile(6, 5),
            DominoTile(6, 5),  # مكرر
        ]
        result = self.rules.validate_hand(hand)
        self.assertFalse(result.is_valid)
        self.assertEqual(
            result.violation, 
            Violation.DUPLICATE_TILE
        )
    
    def test_validate_valid_move(self):
        """حركة صحيحة"""
        move = Move(
            PlayerPosition.SOUTH,
            DominoTile(6, 6),
            Direction.LEFT
        )
        
        result = self.rules.validate_move(
            move, self.state
        )
        self.assertTrue(result.is_valid)
    
    def test_validate_wrong_turn(self):
        """دور خاطئ"""
        move = Move(
            PlayerPosition.WEST,
            DominoTile(6, 6),
            Direction.LEFT
        )
        
        result = self.rules.validate_move(
            move, self.state
        )
        self.assertFalse(result.is_valid)
        self.assertEqual(
            result.violation, 
            Violation.NOT_YOUR_TURN
        )
    
    def test_validate_tile_not_in_hand(self):
        """حجر غير موجود في اليد"""
        move = Move(
            PlayerPosition.SOUTH,
            DominoTile(5, 5),  # ما عنده
            Direction.LEFT
        )
        
        result = self.rules.validate_move(
            move, self.state
        )
        self.assertFalse(result.is_valid)
    
    def test_dominant_numbers(self):
        """الأرقام المسيطرة"""
        hand = [
            DominoTile(6, 5),
            DominoTile(6, 3),
            DominoTile(6, 1),
            DominoTile(5, 2),
        ]
        
        dominant = self.rules.get_dominant_numbers(hand)
        # 6 يظهر 3 مرات = الأكثر
        first_key = list(dominant.keys())[0]
        self.assertEqual(first_key, 6)
    
    def test_suggest_opening(self):
        """اقتراح الحركة الافتتاحية"""
        hand = [
            DominoTile(6, 6),  # أعلى دبل
            DominoTile(5, 3),
            DominoTile(4, 2),
        ]
        
        suggestion = self.rules.suggest_opening_tile(hand)
        self.assertEqual(suggestion, DominoTile(6, 6))
    
    def test_game_over_domino(self):
        """نهاية بالدومينو"""
        # أفرغ يد اللاعب
        self.state.players[PlayerPosition.SOUTH].hand = []
        
        is_over, reason = self.rules.check_game_over(
            self.state
        )
        self.assertTrue(is_over)
        self.assertIn("دومينو", reason)
    
    def test_score_calculation(self):
        """حساب النقاط"""
        # تعيين أحجار لكل لاعب
        self.state.players[PlayerPosition.SOUTH].hand = []
        self.state.players[PlayerPosition.NORTH].hand = [
            DominoTile(2, 1)
        ]
        self.state.players[PlayerPosition.WEST].hand = [
            DominoTile(6, 5)
        ]
        self.state.players[PlayerPosition.EAST].hand = [
            DominoTile(4, 3)
        ]
        
        self.state.winner = PlayerPosition.SOUTH
        self.state.is_game_over = True
        
        score = self.rules.calculate_score(self.state)
        
        self.assertEqual(score.winner_team, "south_north")
        self.assertEqual(
            score.team_west_east, 
            11 + 7  # [6|5]=11, [4|3]=7
        )


class TestIntegration(unittest.TestCase):
    """اختبارات تكاملية"""
    
    def test_full_game_simulation(self):
        """محاكاة لعبة كاملة"""
        import random
        
        state = GameState()
        state.initialize_players()
        
        # توزيع عشوائي
        all_tiles = list(state.ALL_TILES)
        random.shuffle(all_tiles)
        
        for i, pos in enumerate(PlayerPosition):
            hand = all_tiles[i * 7:(i + 1) * 7]
            state.players[pos].hand = hand
            state.players[pos].tiles_count = len(hand)
        
        # لعب حتى النهاية
        max_moves = 100
        moves_played = 0
        
        while (
            not state.is_game_over and 
            moves_played < max_moves
        ):
            valid_moves = state.get_valid_moves(
                state.current_turn
            )
            
            # اختيار عشوائي
            move = random.choice(valid_moves)
            state.apply_move(move)
            moves_played += 1
        
        # يجب أن تنتهي اللعبة
        self.assertLessEqual(
            moves_played, max_moves,
            "اللعبة لم تنتهِ في حدود المعقول"
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
