# game_engine/domino_board.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Set
from enum import Enum
import copy


class Direction(Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class DominoTile:
    """حجر دومينو واحد - غير قابل للتعديل"""
    high: int
    low: int
    
    def __post_init__(self):
        # نضمن أن high >= low دائماً
        if self.high < self.low:
            object.__setattr__(self, 'high', self.low)
            object.__setattr__(self, 'low', self.high)
    
    @property
    def is_double(self) -> bool:
        return self.high == self.low
    
    @property
    def total(self) -> int:
        return self.high + self.low
    
    @property
    def pip_values(self) -> Set[int]:
        return {self.high, self.low}
    
    def has_value(self, value: int) -> bool:
        return value in (self.high, self.low)
    
    def other_side(self, value: int) -> int:
        """إرجاع الجانب الآخر"""
        if value == self.high:
            return self.low
        elif value == self.low:
            return self.high
        raise ValueError(f"القيمة {value} غير موجودة في الحجر {self}")
    
    def __repr__(self):
        return f"[{self.high}|{self.low}]"
    
    def __eq__(self, other):
        if not isinstance(other, DominoTile):
            return False
        return (self.high == other.high and self.low == other.low)
    
    def __hash__(self):
        return hash((self.high, self.low))


@dataclass
class Board:
    """
    طاولة الدومينو - تتبع الأحجار الملعوبة والأطراف المفتوحة
    """
    tiles_played: List[Tuple[DominoTile, Direction]] = field(
        default_factory=list
    )
    left_end: Optional[int] = None
    right_end: Optional[int] = None
    
    @property
    def is_empty(self) -> bool:
        return len(self.tiles_played) == 0
    
    @property
    def open_ends(self) -> Set[int]:
        """الأطراف المفتوحة على الطاولة"""
        if self.is_empty:
            return set()
        ends = {self.left_end, self.right_end}
        return ends
    
    @property
    def all_played_tiles(self) -> List[DominoTile]:
        """كل الأحجار الملعوبة"""
        return [tile for tile, _ in self.tiles_played]
    
    def can_play(self, tile: DominoTile) -> List[Direction]:
        """
        هل يمكن لعب هذا الحجر؟ وفي أي اتجاه؟
        """
        if self.is_empty:
            return [Direction.LEFT]  # أول حجر
        
        valid_directions = []
        
        if tile.has_value(self.left_end):
            valid_directions.append(Direction.LEFT)
        if tile.has_value(self.right_end):
            # تجنب التكرار لو الطرفين نفس الرقم
            if self.left_end != self.right_end or not valid_directions:
                valid_directions.append(Direction.RIGHT)
        
        return valid_directions
    
    def play_tile(self, tile: DominoTile, direction: Direction) -> bool:
        """
        لعب حجر على الطاولة
        """
        if self.is_empty:
            self.tiles_played.append((tile, direction))
            self.left_end = tile.high
            self.right_end = tile.low
            return True
        
        valid_dirs = self.can_play(tile)
        if direction not in valid_dirs:
            return False
        
        if direction == Direction.LEFT:
            # الحجر يتصل بالطرف الأيسر
            if tile.has_value(self.left_end):
                new_end = tile.other_side(self.left_end)
                self.left_end = new_end
            else:
                return False
        else:
            # الحجر يتصل بالطرف الأيمن
            if tile.has_value(self.right_end):
                new_end = tile.other_side(self.right_end)
                self.right_end = new_end
            else:
                return False
        
        self.tiles_played.append((tile, direction))
        return True
    
    def get_played_values_count(self) -> dict:
        """
        عدد مرات ظهور كل رقم على الطاولة
        مهم جداً لحساب احتمالات الخصوم
        """
        count = {}
        for tile, _ in self.tiles_played:
            for val in [tile.high, tile.low]:
                count[val] = count.get(val, 0) + 1
        return count
    
    def clone(self) -> Board:
        """نسخة عميقة للمحاكاة"""
        return copy.deepcopy(self)
    
    def display(self) -> str:
        """عرض الطاولة بشكل مرئي"""
        if self.is_empty:
            return "[ الطاولة فارغة ]"
        
        parts = []
        for tile, direction in self.tiles_played:
            parts.append(str(tile))
        
        chain = " ← ".join(parts)
        return (
            f"الطرف الأيسر [{self.left_end}] "
            f"{'─' * 3} {chain} "
            f"{'─' * 3} [{self.right_end}] الطرف الأيمن"
        )
