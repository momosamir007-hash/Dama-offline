# game_engine/__init__.py
"""
محرك لعبة الدومينو
يدير حالة اللعبة والقواعد والتحقق من الحركات
"""

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import (
    GameState, 
    PlayerPosition, 
    PlayerInfo, 
    Move
)
from game_engine.rules import DominoRules, GameMode, Violation

__all__ = [
    'DominoTile',
    'Board', 
    'Direction',
    'GameState',
    'PlayerPosition',
    'PlayerInfo',
    'Move',
    'DominoRules',
    'GameMode',
    'Violation',
]
