# game_engine/game_state.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Tuple
from enum import Enum
import random
import copy

from game_engine.domino_board import DominoTile, Board, Direction


class PlayerPosition(Enum):
    """مواقع اللاعبين - أنت دائماً SOUTH"""
    SOUTH = 0      # أنت
    WEST = 1       # يمينك
    NORTH = 2      # شريكك (قدامك)
    EAST = 3       # يسارك


@dataclass
class PlayerInfo:
    position: PlayerPosition
    hand: List[DominoTile] = field(default_factory=list)
    tiles_count: int = 7       # عدد الأحجار المتبقية (للخصوم)
    passed_values: Set[int] = field(default_factory=set)  # الأرقام اللي "دق" عليها
    played_tiles: List[DominoTile] = field(default_factory=list)  # اللي لعبها
    is_me: bool = False
    
    @property
    def hand_total(self) -> int:
        """مجموع نقاط اليد"""
        return sum(t.total for t in self.hand)
    
    def remove_tile(self, tile: DominoTile) -> bool:
        if tile in self.hand:
            self.hand.remove(tile)
            self.tiles_count = len(self.hand)
            return True
        return False


@dataclass
class Move:
    """حركة واحدة"""
    player: PlayerPosition
    tile: Optional[DominoTile]       # None = دق (pass)
    direction: Optional[Direction]
    
    @property
    def is_pass(self) -> bool:
        return self.tile is None
    
    def __repr__(self):
        if self.is_pass:
            return f"{self.player.name}: دَقّ (Pass)"
        return f"{self.player.name}: {self.tile} → {self.direction.value}"


@dataclass 
class GameState:
    """
    الحالة الكاملة للعبة في أي لحظة
    هذا هو القلب النابض للنظام
    """
    board: Board = field(default_factory=Board)
    players: Dict[PlayerPosition, PlayerInfo] = field(default_factory=dict)
    current_turn: PlayerPosition = PlayerPosition.SOUTH
    move_history: List[Move] = field(default_factory=list)
    consecutive_passes: int = 0
    is_game_over: bool = False
    winner: Optional[PlayerPosition] = None
    
    # كل أحجار الدومينو الممكنة
    ALL_TILES: Set[DominoTile] = field(default_factory=set, init=False)
    
    def __post_init__(self):
        # توليد كل 28 حجر
        self.ALL_TILES = {
            DominoTile(i, j) 
            for i in range(7) 
            for j in range(i + 1)  # i >= j
        }
        # هنا يجب أن يكون i >= j لتجنب التكرار
        # لكن DominoTile.__post_init__ يتولى الترتيب
        self.ALL_TILES = set()
        for i in range(7):
            for j in range(i, 7):
                self.ALL_TILES.add(DominoTile(j, i))
    
    def initialize_players(self):
        """تهيئة اللاعبين"""
        for pos in PlayerPosition:
            self.players[pos] = PlayerInfo(
                position=pos,
                is_me=(pos == PlayerPosition.SOUTH)
            )
    
    def set_my_hand(self, tiles: List[DominoTile]):
        """تعيين أحجاري"""
        me = self.players[PlayerPosition.SOUTH]
        me.hand = tiles.copy()
        me.tiles_count = len(tiles)
    
    @property
    def my_hand(self) -> List[DominoTile]:
        return self.players[PlayerPosition.SOUTH].hand
    
    @property
    def known_tiles(self) -> Set[DominoTile]:
        """
        الأحجار المعروفة:
        - أحجاري
        - الأحجار الملعوبة على الطاولة
        """
        known = set(self.my_hand)
        known.update(self.board.all_played_tiles)
        return known
    
    @property
    def unknown_tiles(self) -> Set[DominoTile]:
        """
        الأحجار المجهولة (عند الخصوم)
        """
        return self.ALL_TILES - self.known_tiles
    
    def get_valid_moves(
        self, 
        player: PlayerPosition
    ) -> List[Move]:
        """
        كل الحركات المسموحة للاعب معين
        """
        player_info = self.players[player]
        moves = []
        
        if self.board.is_empty:
            # أول حركة
            for tile in player_info.hand:
                moves.append(Move(player, tile, Direction.LEFT))
            return moves if moves else [Move(player, None, None)]
        
        for tile in player_info.hand:
            valid_dirs = self.board.can_play(tile)
            for direction in valid_dirs:
                moves.append(Move(player, tile, direction))
        
        # لو ما فيه حركة = دق
        if not moves:
            moves.append(Move(player, None, None))
        
        return moves
    
    def apply_move(self, move: Move) -> bool:
        """تطبيق حركة على حالة اللعبة"""
        player_info = self.players[move.player]
        
        if move.is_pass:
            # تسجيل أرقام الأطراف المفتوحة كأرقام "مدقوقة"
            if not self.board.is_empty:
                player_info.passed_values.update(self.board.open_ends)
            
            self.consecutive_passes += 1
            
            # لو كل اللاعبين دقوا = اللعبة مقفلة
            if self.consecutive_passes >= 4:
                self.is_game_over = True
                self._determine_winner_by_count()
        else:
            # لعب الحجر
            success = self.board.play_tile(move.tile, move.direction)
            if not success:
                return False
            
            player_info.remove_tile(move.tile)
            player_info.played_tiles.append(move.tile)
            player_info.tiles_count -= 1
            self.consecutive_passes = 0
            
            # هل اللاعب خلّص أحجاره؟
            if player_info.tiles_count <= 0:
                # لو الأحجار معروفة (أنا)
                if not player_info.hand or len(player_info.hand) == 0:
                    self.is_game_over = True
                    self.winner = move.player
        
        self.move_history.append(move)
        self._advance_turn()
        return True
    
    def _advance_turn(self):
        """الدور التالي"""
        current = self.current_turn.value
        self.current_turn = PlayerPosition((current + 1) % 4)
    
    def _determine_winner_by_count(self):
        """تحديد الفائز عند القفل بالنقاط"""
        min_total = float('inf')
        winner = None
        
        for pos, player in self.players.items():
            total = player.hand_total
            if total < min_total:
                min_total = total
                winner = pos
        
        self.winner = winner
    
    def get_remaining_count_per_value(self) -> Dict[int, int]:
        """
        كم حجر متبقي يحتوي على كل رقم
        أساسي لحساب الاحتمالات
        """
        # كل رقم يظهر في 7 أحجار (من 0 لـ 6)
        total_per_value = {i: 0 for i in range(7)}
        
        for tile in self.ALL_TILES:
            if tile.is_double:
                total_per_value[tile.high] += 1
            else:
                total_per_value[tile.high] += 1
                total_per_value[tile.low] += 1
        
        # نطرح المعروفة
        played_count = {i: 0 for i in range(7)}
        for tile in self.known_tiles:
            if tile.is_double:
                played_count[tile.high] += 1
            else:
                played_count[tile.high] += 1
                played_count[tile.low] += 1
        
        remaining = {
            i: total_per_value[i] - played_count[i] 
            for i in range(7)
        }
        return remaining
    
    def clone(self) -> GameState:
        """نسخة عميقة للمحاكاة"""
        return copy.deepcopy(self)
    
    def display_status(self) -> str:
        """عرض حالة اللعبة"""
        lines = [
            "=" * 60,
            "حالة اللعبة",
            "=" * 60,
            "",
            f"الطاولة: {self.board.display()}",
            "",
            f"أحجارك: {self.my_hand}",
            f"مجموع نقاطك: {self.players[PlayerPosition.SOUTH].hand_total}",
            "",
        ]
        
        for pos in [
            PlayerPosition.WEST, 
            PlayerPosition.NORTH, 
            PlayerPosition.EAST
        ]:
            p = self.players[pos]
            passed = (
                ", ".join(map(str, p.passed_values)) 
                if p.passed_values else "لا شيء"
            )
            lines.append(
                f"{pos.name}: "
                f"{p.tiles_count} أحجار متبقية | "
                f"دق على: {passed}"
            )
        
        lines.extend([
            "",
            f"الدور: {self.current_turn.name}",
            f"الأحجار المجهولة: {len(self.unknown_tiles)} حجر",
            "=" * 60
        ])
        
        return "\n".join(lines)
