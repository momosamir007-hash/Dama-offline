"""
أدوات مساعدة - بدون أي استيراد من svg_renderer
"""
import streamlit as st
import json
import os
import time
import copy
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import GameState, PlayerPosition, Move

# ─── لا نستورد svg_renderer هنا أبداً ───

PLAYER_NAMES = {
    PlayerPosition.SOUTH: "أنت",
    PlayerPosition.WEST: "الخصم الأيمن",
    PlayerPosition.NORTH: "شريكك",
    PlayerPosition.EAST: "الخصم الأيسر",
}

PLAYER_ICONS = {
    PlayerPosition.SOUTH: "🟢",
    PlayerPosition.WEST: "🔴",
    PlayerPosition.NORTH: "🔵",
    PlayerPosition.EAST: "🟠",
}


class SessionManager:
    DEFAULTS = {
        'game_state': None,
        'game_started': False,
        'game_phase': 'setup',
        'my_hand_input': [],
        'ai_recommendation': None,
        'ai_analysis': None,
        'ai_strategy': None,
        'move_history_display': [],
        'mcts_simulations': 1000,
        'mcts_time': 3.0,
        'show_probabilities': False,
        'message': '',
        'message_type': 'info',
        'captured_hand_photo': None,
    }

    @classmethod
    def init(cls):
        for key, val in cls.DEFAULTS.items():
            if key not in st.session_state:
                if isinstance(val, (list, dict)):
                    st.session_state[key] = copy.deepcopy(val)
                else:
                    st.session_state[key] = val

    @classmethod
    def get(cls, key, default=None):
        return st.session_state.get(
            key, default if default is not None else cls.DEFAULTS.get(key)
        )

    @classmethod
    def set(cls, key, value):
        st.session_state[key] = value

    @classmethod
    def reset_game(cls):
        keys_to_reset = [
            'game_state', 'game_started', 'game_phase',
            'my_hand_input', 'ai_recommendation', 'ai_analysis',
            'ai_strategy', 'move_history_display', 'message',
            'message_type', 'captured_hand_photo',
        ]
        for key in keys_to_reset:
            val = cls.DEFAULTS.get(key)
            if isinstance(val, (list, dict)):
                st.session_state[key] = copy.deepcopy(val)
            else:
                st.session_state[key] = val

    @classmethod
    def generate_game_id(cls):
        return str(int(time.time()))[-8:]


class Formatter:
    @staticmethod
    def move_to_text(move):
        name = PLAYER_NAMES.get(move.player, "?")
        icon = PLAYER_ICONS.get(move.player, "⚪")
        if move.is_pass:
            return f"{icon} {name}: دق 🚫"
        d = "⬅️ يسار" if move.direction == Direction.LEFT else "➡️ يمين"
        return f"{icon} {name}: [{move.tile.high}|{move.tile.low}] {d}"

    @staticmethod
    def format_number(num):
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)

    @staticmethod
    def format_percentage(val):
        return f"{val * 100:.1f}%"

    @staticmethod
    def format_duration(secs):
        if secs < 60:
            return f"{secs:.1f} ثانية"
        return f"{int(secs // 60)} دقيقة و {int(secs % 60)} ثانية"


class NotificationManager:
    @staticmethod
    def show_toast(msg, toast_type="info"):
        icons = {
            'info': 'ℹ️', 'success': '✅',
            'warning': '⚠️', 'error': '❌',
        }
        st.toast(msg, icon=icons.get(toast_type, 'ℹ️'))

    @staticmethod
    def show_banner(msg, btype="info"):
        funcs = {
            'info': st.info,
            'success': st.success,
            'warning': st.warning,
            'error': st.error,
        }
        funcs.get(btype, st.info)(msg)


class StyleManager:
    @staticmethod
    def load_css(filepath="assets/style.css"):
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                st.markdown(
                    f"<style>{f.read()}</style>",
                    unsafe_allow_html=True,
                )


class PlayerStats:
    FILE = "player_stats.json"

    @classmethod
    def _load(cls):
        if os.path.exists(cls.FILE):
            try:
                with open(cls.FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            'total_games': 0, 'wins': 0,
            'losses': 0, 'draws': 0,
            'total_moves': 0, 'best_streak': 0,
            'current_streak': 0, 'tiles_played': {},
            'game_history': [], 'total_points_won': 0,
            'total_points_lost': 0, 'game_durations': [],
        }

    @classmethod
    def _save(cls, stats):
        with open(cls.FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    @classmethod
    def record_game(cls, result, moves_count, **kwargs):
        stats = cls._load()
        stats['total_games'] += 1
        stats['total_moves'] += moves_count
        if result == 'win':
            stats['wins'] += 1
            stats['current_streak'] += 1
            stats['best_streak'] = max(
                stats['best_streak'], stats['current_streak']
            )
        elif result == 'loss':
            stats['losses'] += 1
            stats['current_streak'] = 0
        else:
            stats['draws'] += 1
        stats['game_history'].append({
            'date': datetime.now().isoformat(),
            'result': result,
            'moves': moves_count,
        })
        stats['game_history'] = stats['game_history'][-100:]
        cls._save(stats)

    @classmethod
    def get_stats(cls):
        return cls._load()

    @classmethod
    def get_win_rate(cls):
        s = cls._load()
        t = s['total_games']
        return s['wins'] / t if t else 0

    @classmethod
    def get_favorite_tile(cls):
        s = cls._load()
        t = s.get('tiles_played', {})
        return max(t, key=t.get) if t else None

    @classmethod
    def reset(cls):
        if os.path.exists(cls.FILE):
            os.remove(cls.FILE)


class ExportTools:
    @staticmethod
    def generate_game_report(state, analysis=None):
        lines = [
            "# تقرير لعبة الدومينو",
            f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## الطاولة",
            f"الأيسر: {state.board.left_end} | الأيمن: {state.board.right_end}",
            f"أحجار: {len(state.board.tiles_played)}",
            "",
            f"## الحركات ({len(state.move_history)})",
        ]
        for i, m in enumerate(state.move_history, 1):
            lines.append(f"{i}. {Formatter.move_to_text(m)}")
        return "\n".join(lines)


def generate_all_tiles(max_pip=6):
    tiles = []
    for i in range(max_pip + 1):
        for j in range(i, max_pip + 1):
            tiles.append(DominoTile(j, i))
    return tiles


def get_playable_tiles(hand, board):
    if board.is_empty:
        return list(range(len(hand)))
    return [i for i, t in enumerate(hand) if board.can_play(t)]
