# game_engine/rules.py
"""
قواعد لعبة الدومينو الكاملة
يدعم عدة أوضاع:
  - المصري (Egyptian)
  - الكلاسيكي (Classic/Block)
  - السحب (Draw)
  - الشراكة (Partnership)

هذا الملف هو "الحَكَم" الذي يتحقق من صحة كل شيء
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import (
    List, Optional, Dict, Set, 
    Tuple, Callable
)
from enum import Enum
import itertools

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo, Move
)


# ──────────────────────────────────────────────
# التعدادات والثوابت
# ──────────────────────────────────────────────

class GameMode(Enum):
    """أوضاع اللعب المدعومة"""
    EGYPTIAN = "egyptian"           # المصري - 4 لاعبين شراكة
    CLASSIC_BLOCK = "classic_block" # الكلاسيكي - بدون سحب
    DRAW = "draw"                   # السحب من البيار
    PARTNERSHIP = "partnership"     # شراكة عامة


class Violation(Enum):
    """أنواع المخالفات"""
    TILE_NOT_IN_HAND = "الحجر غير موجود في يدك"
    INVALID_DIRECTION = "لا يمكن اللعب في هذا الاتجاه"
    BOARD_MISMATCH = "الحجر لا يتطابق مع أطراف الطاولة"
    NOT_YOUR_TURN = "ليس دورك"
    GAME_ALREADY_OVER = "اللعبة انتهت"
    INVALID_FIRST_MOVE = "حركة افتتاحية غير صحيحة"
    CAN_PLAY_NOT_PASS = "لا يمكنك الدق وعندك حجر مناسب"
    DUPLICATE_TILE = "هذا الحجر موجود مسبقاً"
    INVALID_TILE_VALUES = "أرقام الحجر غير صحيحة"
    HAND_SIZE_EXCEEDED = "عدد الأحجار تجاوز الحد"


@dataclass
class RuleCheckResult:
    """نتيجة التحقق من قاعدة"""
    is_valid: bool
    violation: Optional[Violation] = None
    message: str = ""
    
    @staticmethod
    def ok(message: str = "") -> RuleCheckResult:
        return RuleCheckResult(
            is_valid=True, message=message
        )
    
    @staticmethod
    def fail(
        violation: Violation, 
        detail: str = ""
    ) -> RuleCheckResult:
        msg = f"{violation.value}"
        if detail:
            msg += f" - {detail}"
        return RuleCheckResult(
            is_valid=False,
            violation=violation,
            message=msg
        )


@dataclass
class ScoreResult:
    """نتيجة حساب النقاط"""
    team_south_north: int = 0    # فريق أنت + شريكك
    team_west_east: int = 0      # فريق الخصوم
    winner_team: Optional[str] = None
    details: Dict[PlayerPosition, int] = field(
        default_factory=dict
    )
    bonus_points: int = 0
    reason: str = ""


# ──────────────────────────────────────────────
# القواعد الأساسية
# ──────────────────────────────────────────────

class DominoRules:
    """
    الحكم الرئيسي - يتحقق من كل القواعد
    ويحسب النقاط ويحدد الفائز
    """
    
    def __init__(
        self, 
        mode: GameMode = GameMode.EGYPTIAN,
        max_pip: int = 6,
        hand_size: int = 7,
        num_players: int = 4,
        target_score: int = 151
    ):
        self.mode = mode
        self.max_pip = max_pip
        self.hand_size = hand_size
        self.num_players = num_players
        self.target_score = target_score
        
        # توليد مجموعة الأحجار الكاملة
        self.all_tiles = self._generate_all_tiles()
        self.total_tiles = len(self.all_tiles)
    
    # ──────────────────────────────────────────
    # توليد الأحجار
    # ──────────────────────────────────────────
    
    def _generate_all_tiles(self) -> Set[DominoTile]:
        """
        توليد كل أحجار الدومينو الممكنة
        
        دومينو 6|6 = 28 حجر:
        [0|0] [1|0] [1|1] [2|0] [2|1] [2|2] ...
        
        الصيغة العامة: (n+1)(n+2)/2
        حيث n = max_pip
        """
        tiles = set()
        for i in range(self.max_pip + 1):
            for j in range(i, self.max_pip + 1):
                tiles.add(DominoTile(j, i))
        return tiles
    
    # ──────────────────────────────────────────
    # التحقق من الأحجار
    # ──────────────────────────────────────────
    
    def validate_tile(
        self, tile: DominoTile
    ) -> RuleCheckResult:
        """التحقق من صحة حجر"""
        if tile.high < 0 or tile.low < 0:
            return RuleCheckResult.fail(
                Violation.INVALID_TILE_VALUES,
                f"أرقام سالبة: {tile}"
            )
        
        if tile.high > self.max_pip or tile.low > self.max_pip:
            return RuleCheckResult.fail(
                Violation.INVALID_TILE_VALUES,
                f"رقم أكبر من {self.max_pip}: {tile}"
            )
        
        if tile not in self.all_tiles:
            return RuleCheckResult.fail(
                Violation.INVALID_TILE_VALUES,
                f"حجر غير موجود في المجموعة: {tile}"
            )
        
        return RuleCheckResult.ok()
    
    def validate_hand(
        self, 
        hand: List[DominoTile]
    ) -> RuleCheckResult:
        """التحقق من صحة يد اللاعب"""
        # التحقق من العدد
        if len(hand) > self.hand_size:
            return RuleCheckResult.fail(
                Violation.HAND_SIZE_EXCEEDED,
                f"عدد الأحجار {len(hand)} > {self.hand_size}"
            )
        
        # التحقق من التكرار
        seen = set()
        for tile in hand:
            if tile in seen:
                return RuleCheckResult.fail(
                    Violation.DUPLICATE_TILE,
                    f"الحجر {tile} مكرر"
                )
            seen.add(tile)
        
        # التحقق من صحة كل حجر
        for tile in hand:
            result = self.validate_tile(tile)
            if not result.is_valid:
                return result
        
        return RuleCheckResult.ok()
    
    # ──────────────────────────────────────────
    # التحقق من الحركات
    # ──────────────────────────────────────────
    
    def validate_move(
        self,
        move: Move,
        state: GameState
    ) -> RuleCheckResult:
        """
        التحقق الشامل من صحة الحركة
        
        يتحقق من:
        1. هل اللعبة لا تزال جارية
        2. هل الدور صحيح
        3. هل الحجر موجود في اليد
        4. هل الحجر يتطابق مع الطاولة
        5. هل الاتجاه صحيح
        6. هل يحق له الدق (لا يملك حجراً مناسباً)
        """
        # 1. هل اللعبة انتهت؟
        if state.is_game_over:
            return RuleCheckResult.fail(
                Violation.GAME_ALREADY_OVER
            )
        
        # 2. هل الدور صحيح؟
        if move.player != state.current_turn:
            return RuleCheckResult.fail(
                Violation.NOT_YOUR_TURN,
                f"الدور لـ {state.current_turn.name} "
                f"وليس {move.player.name}"
            )
        
        # 3. حالة الدق (Pass)
        if move.is_pass:
            return self._validate_pass(move, state)
        
        # 4. التحقق من الحجر
        player = state.players[move.player]
        
        # هل الحجر في اليد (للاعب المعروف)
        if player.is_me and move.tile not in player.hand:
            return RuleCheckResult.fail(
                Violation.TILE_NOT_IN_HAND,
                f"الحجر {move.tile} غير موجود في يدك"
            )
        
        # 5. التحقق من التطابق مع الطاولة
        if state.board.is_empty:
            return self._validate_first_move(move, state)
        
        # 6. هل الاتجاه صحيح؟
        valid_directions = state.board.can_play(move.tile)
        
        if not valid_directions:
            return RuleCheckResult.fail(
                Violation.BOARD_MISMATCH,
                f"الحجر {move.tile} لا يتطابق مع "
                f"أطراف الطاولة "
                f"[{state.board.left_end}] و "
                f"[{state.board.right_end}]"
            )
        
        if move.direction not in valid_directions:
            return RuleCheckResult.fail(
                Violation.INVALID_DIRECTION,
                f"لا يمكن لعب {move.tile} على "
                f"الجهة {move.direction.value}. "
                f"الاتجاهات المتاحة: "
                f"{[d.value for d in valid_directions]}"
            )
        
        return RuleCheckResult.ok(
            f"حركة صحيحة: {move}"
        )
    
    def _validate_pass(
        self,
        move: Move,
        state: GameState
    ) -> RuleCheckResult:
        """
        التحقق من صحة الدق
        لا يحق للاعب الدق إذا كان يملك حجراً مناسباً
        """
        player = state.players[move.player]
        
        # للاعب المعروف (أنت): نتحقق من يده
        if player.is_me or player.hand:
            for tile in player.hand:
                if state.board.can_play(tile):
                    return RuleCheckResult.fail(
                        Violation.CAN_PLAY_NOT_PASS,
                        f"عندك حجر مناسب: {tile}"
                    )
        
        return RuleCheckResult.ok("دق صحيح")
    
    def _validate_first_move(
        self,
        move: Move,
        state: GameState
    ) -> RuleCheckResult:
        """
        التحقق من الحركة الافتتاحية
        
        القواعد تختلف حسب الوضع:
        - المصري: أعلى دبل يبدأ
        - الكلاسيكي: أي حجر
        """
        if self.mode == GameMode.EGYPTIAN:
            # في الدور الأول فقط: يجب البدء بأعلى دبل
            if len(state.move_history) == 0:
                # نتحقق هل هذا أعلى دبل متاح
                highest_double = self._find_highest_double(
                    state
                )
                if highest_double and move.tile != highest_double:
                    # ممكن يكون أعلى دبل عند لاعب آخر
                    # فنسمح بأي حجر لو ما عنده دبل
                    player = state.players[move.player]
                    player_doubles = [
                        t for t in player.hand 
                        if t.is_double
                    ]
                    if player_doubles:
                        max_double = max(
                            player_doubles, 
                            key=lambda t: t.high
                        )
                        if move.tile != max_double:
                            return RuleCheckResult.fail(
                                Violation.INVALID_FIRST_MOVE,
                                f"يجب البدء بأعلى دبل: "
                                f"{max_double}"
                            )
        
        return RuleCheckResult.ok("حركة افتتاحية صحيحة")
    
    def _find_highest_double(
        self, 
        state: GameState
    ) -> Optional[DominoTile]:
        """إيجاد أعلى دبل بين كل اللاعبين"""
        highest = None
        for pos, player in state.players.items():
            for tile in player.hand:
                if tile.is_double:
                    if highest is None or tile.high > highest.high:
                        highest = tile
        return highest
    
    # ──────────────────────────────────────────
    # التحقق من نهاية اللعبة
    # ──────────────────────────────────────────
    
    def check_game_over(
        self, 
        state: GameState
    ) -> Tuple[bool, Optional[str]]:
        """
        هل اللعبة انتهت؟
        
        تنتهي عندما:
        1. لاعب خلّص كل أحجاره (دومينو!)
        2. كل اللاعبين دقوا (قفل/lock)
        
        Returns:
            (انتهت؟, السبب)
        """
        # 1. لاعب خلّص أحجاره
        for pos, player in state.players.items():
            if player.is_me and len(player.hand) == 0:
                return True, f"دومينو! {pos.name} خلّص أحجاره"
            elif (
                not player.is_me and 
                player.tiles_count <= 0
            ):
                return True, f"دومينو! {pos.name} خلّص أحجاره"
        
        # 2. قفل - كل اللاعبين دقوا
        if state.consecutive_passes >= self.num_players:
            return True, "قفل! كل اللاعبين دقوا"
        
        # 3. تحقق إضافي: هل يمكن لأي لاعب أن يلعب؟
        if not state.board.is_empty:
            all_stuck = self._check_all_stuck(state)
            if all_stuck:
                return True, "قفل! لا أحد يستطيع اللعب"
        
        return False, None
    
    def _check_all_stuck(
        self, 
        state: GameState
    ) -> bool:
        """
        هل كل اللاعبين عالقون؟
        (ما يقدرون يلعبون أي حجر)
        
        ملاحظة: للخصوم ما نعرف أحجارهم بالضبط
        فنتحقق فقط من اللاعب المعروف
        """
        me = state.players[PlayerPosition.SOUTH]
        my_moves = state.get_valid_moves(PlayerPosition.SOUTH)
        
        # لو أنا عندي حركة = ما في قفل
        has_real_move = any(
            not m.is_pass for m in my_moves
        )
        
        if has_real_move:
            return False
        
        # لو ما عندي حركة + 3 دقات متتالية = قفل
        return state.consecutive_passes >= 3
    
    # ──────────────────────────────────────────
    # حساب النقاط
    # ──────────────────────────────────────────
    
    def calculate_score(
        self, 
        state: GameState
    ) -> ScoreResult:
        """
        حساب نقاط الجولة
        
        الطريقة المصرية:
        - لو دومينو: الفائز ياخذ مجموع نقاط الخصوم
        - لو قفل: أقل مجموع نقاط يفوز
        - نقاط البونص: دبل 6-6 آخر حجر = بونص
        """
        result = ScoreResult()
        
        # حساب مجموع كل لاعب
        for pos, player in state.players.items():
            hand_total = player.hand_total
            result.details[pos] = hand_total
        
        # مجموع الفرق
        result.team_south_north = (
            result.details.get(PlayerPosition.SOUTH, 0) +
            result.details.get(PlayerPosition.NORTH, 0)
        )
        
        result.team_west_east = (
            result.details.get(PlayerPosition.WEST, 0) +
            result.details.get(PlayerPosition.EAST, 0)
        )
        
        # تحديد الفائز
        if state.winner:
            # دومينو - لاعب خلّص أحجاره
            result = self._score_domino(state, result)
        else:
            # قفل
            result = self._score_lock(state, result)
        
        # بونص
        result.bonus_points = self._calculate_bonus(state)
        
        return result
    
    def _score_domino(
        self, 
        state: GameState,
        result: ScoreResult
    ) -> ScoreResult:
        """حساب نقاط الدومينو"""
        winner = state.winner
        
        if winner in (
            PlayerPosition.SOUTH, 
            PlayerPosition.NORTH
        ):
            # فريقنا فاز
            # نأخذ نقاط الخصوم
            score = result.team_west_east
            result.winner_team = "south_north"
            result.reason = (
                f"دومينو! {winner.name} خلّص. "
                f"كسب {score} نقطة من الخصوم"
            )
        else:
            # الخصم فاز
            score = result.team_south_north
            result.winner_team = "west_east"
            result.reason = (
                f"دومينو! {winner.name} خلّص. "
                f"خسرنا {score} نقطة"
            )
        
        return result
    
    def _score_lock(
        self,
        state: GameState,
        result: ScoreResult
    ) -> ScoreResult:
        """حساب نقاط القفل"""
        if result.team_south_north < result.team_west_east:
            result.winner_team = "south_north"
            diff = (
                result.team_west_east - 
                result.team_south_north
            )
            result.reason = (
                f"قفل! فريقنا أقل بـ {diff} نقطة"
            )
        elif result.team_west_east < result.team_south_north:
            result.winner_team = "west_east"
            diff = (
                result.team_south_north - 
                result.team_west_east
            )
            result.reason = (
                f"قفل! خسرنا بفرق {diff} نقطة"
            )
        else:
            result.winner_team = None
            result.reason = "قفل! تعادل بالنقاط"
        
        return result
    
    def _calculate_bonus(
        self, 
        state: GameState
    ) -> int:
        """
        حساب نقاط البونص
        
        بونص مصري:
        - دومينو بدبل كبير = 10 نقاط إضافية
        - دومينو من أول حركة = 25 نقطة
        """
        bonus = 0
        
        if state.winner and state.move_history:
            last_move = state.move_history[-1]
            
            # لو آخر حجر كان دبل
            if (
                last_move.tile and 
                last_move.tile.is_double
            ):
                bonus += 10
                
                # دبل 6-6 = بونص إضافي
                if last_move.tile == DominoTile(6, 6):
                    bonus += 15
        
        return bonus
    
    # ──────────────────────────────────────────
    # أدوات مساعدة
    # ──────────────────────────────────────────
    
    def get_all_possible_moves(
        self,
        hand: List[DominoTile],
        board: Board
    ) -> List[Tuple[DominoTile, Direction]]:
        """
        كل الحركات الممكنة ليد معينة على طاولة معينة
        """
        moves = []
        
        for tile in hand:
            directions = board.can_play(tile)
            for direction in directions:
                moves.append((tile, direction))
        
        return moves
    
    def is_locked(self, state: GameState) -> bool:
        """هل اللعبة مقفلة؟"""
        if state.board.is_empty:
            return False
        
        # التحقق من كل الأحجار المتبقية
        remaining_tiles = (
            state.ALL_TILES - 
            set(state.board.all_played_tiles)
        )
        
        for tile in remaining_tiles:
            if state.board.can_play(tile):
                return False
        
        return True
    
    def get_dominant_numbers(
        self,
        hand: List[DominoTile]
    ) -> Dict[int, int]:
        """
        الأرقام المسيطرة في يد اللاعب
        
        Returns:
            {رقم: عدد مرات ظهوره}
            مرتب من الأكثر للأقل
        """
        count = {}
        for tile in hand:
            for val in tile.pip_values:
                count[val] = count.get(val, 0) + 1
        
        # ترتيب
        sorted_count = dict(
            sorted(
                count.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
        )
        
        return sorted_count
    
    def tiles_remaining_for_value(
        self,
        value: int,
        known_tiles: Set[DominoTile]
    ) -> List[DominoTile]:
        """
        الأحجار المتبقية التي تحتوي على رقم معين
        """
        remaining = []
        for tile in self.all_tiles:
            if tile not in known_tiles and tile.has_value(value):
                remaining.append(tile)
        return remaining
    
    def suggest_opening_tile(
        self,
        hand: List[DominoTile]
    ) -> Optional[DominoTile]:
        """
        اقتراح أفضل حجر افتتاحي
        
        الاستراتيجية:
        1. أعلى دبل (إذا وجد)
        2. الحجر من الرقم المسيطر
        """
        # البحث عن أعلى دبل
        doubles = [t for t in hand if t.is_double]
        if doubles:
            return max(doubles, key=lambda t: t.high)
        
        # لو ما فيه دبل: الحجر الأثقل من الرقم المسيطر
        dominant = self.get_dominant_numbers(hand)
        if dominant:
            best_num = list(dominant.keys())[0]
            candidates = [
                t for t in hand 
                if t.has_value(best_num)
            ]
            return max(candidates, key=lambda t: t.total)
        
        # افتراضي: أثقل حجر
        return max(hand, key=lambda t: t.total)
    
    def display_rules(self) -> str:
        """عرض قواعد الوضع الحالي"""
        rules_text = {
            GameMode.EGYPTIAN: """
╔═══════════════════════════════════════╗
║         قواعد الدومينو المصري         ║
╠═══════════════════════════════════════╣
║ • 4 لاعبين في فريقين (شراكة)         ║
║ • كل لاعب 7 أحجار                    ║
║ • صاحب أعلى دبل يبدأ                 ║
║ • اللعب بالدور (عكس عقارب الساعة)     ║
║ • لو ما عندك حجر مناسب = دق           ║
║ • لو الكل دق = قفل                    ║
║ • الفائز: اللي يخلّص أحجاره أولاً      ║
║ • في القفل: أقل مجموع نقاط يفوز       ║
║ • الهدف: 151 نقطة                      ║
╚═══════════════════════════════════════╝
            """,
            GameMode.CLASSIC_BLOCK: """
╔═══════════════════════════════════════╗
║       قواعد الدومينو الكلاسيكي        ║
╠═══════════════════════════════════════╣
║ • 2-4 لاعبين                          ║
║ • أعلى دبل يبدأ                       ║
║ • اللعب بالدور                        ║
║ • بدون سحب من البيار                  ║
║ • الفائز: أول من يخلّص أحجاره          ║
╚═══════════════════════════════════════╝
            """,
            GameMode.DRAW: """
╔═══════════════════════════════════════╗
║         قواعد دومينو السحب            ║
╠═══════════════════════════════════════╣
║ • 2-4 لاعبين                          ║
║ • لو ما عندك حجر: تسحب من البيار      ║
║ • تستمر بالسحب حتى تلاقي حجر مناسب   ║
║ • لو البيار خلص = دق                   ║
╚═══════════════════════════════════════╝
            """,
        }
        
        return rules_text.get(
            self.mode, 
            "قواعد غير محددة"
        )
