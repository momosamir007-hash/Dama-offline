# streamlit_utils.py
"""
أدوات مساعدة لتطبيق Streamlit
يحتوي على:
  - إدارة الحالة (Session State Manager)
  - مكونات واجهة مشتركة (Shared UI Components)
  - تحميل وحفظ الألعاب
  - أدوات التحويل والتنسيق
  - مدير الإشعارات
  - مدير السمات
  - أدوات التصدير
"""

from __future__ import annotations
import streamlit as st
import json
import time
import base64
import io
import os
import hashlib
from datetime import datetime
from typing import (
    List, Dict, Optional, Tuple,
    Any, Callable, Union
)
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

# إعداد المسار
import sys
sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__))
)

from game_engine.domino_board import (
    DominoTile, Board, Direction
)
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo, Move
)
from game_engine.rules import DominoRules, GameMode
from svg_renderer import DominoSVG, TileTheme


# ──────────────────────────────────────────────
# الثوابت
# ──────────────────────────────────────────────

APP_VERSION = "1.0.0"
APP_NAME = "المساعد الذكي للدومينو"
SAVE_DIR = "saves"
STATS_FILE = "player_stats.json"

PLAYER_NAMES = {
    PlayerPosition.SOUTH: "أنت",
    PlayerPosition.WEST: "الخصم الأيمن (غرب)",
    PlayerPosition.NORTH: "شريكك (شمال)",
    PlayerPosition.EAST: "الخصم الأيسر (شرق)",
}

PLAYER_ICONS = {
    PlayerPosition.SOUTH: "🟢",
    PlayerPosition.WEST: "🔴",
    PlayerPosition.NORTH: "🔵",
    PlayerPosition.EAST: "🟠",
}

PLAYER_COLORS = {
    PlayerPosition.SOUTH: "#4CAF50",
    PlayerPosition.WEST: "#F44336",
    PlayerPosition.NORTH: "#2196F3",
    PlayerPosition.EAST: "#FF9800",
}


# ──────────────────────────────────────────────
# إدارة الحالة
# ──────────────────────────────────────────────

class SessionManager:
    """
    مدير حالة الجلسة
    يوفر واجهة نظيفة للتعامل مع st.session_state
    """

    # المفاتيح الافتراضية وقيمها
    DEFAULTS = {
        # اللعبة
        'game_state': None,
        'game_started': False,
        'game_phase': 'setup',
        'game_mode': 'egyptian',
        'game_id': '',

        # الإدخال
        'my_hand_input': [],
        'selected_tile_index': -1,

        # الذكاء الاصطناعي
        'ai_recommendation': None,
        'ai_analysis': None,
        'ai_strategy': None,
        'ai_thinking': False,

        # السجل
        'move_history_display': [],
        'games_played': 0,
        'games_won': 0,

        # الإعدادات
        'theme': TileTheme.MODERN,
        'show_probabilities': False,
        'show_animation': True,
        'mcts_simulations': 1000,
        'mcts_time': 3.0,
        'sound_enabled': False,
        'language': 'ar',

        # الرسائل
        'message': '',
        'message_type': 'info',
        'toast_queue': [],

        # التدريب
        'training_running': False,
        'training_progress': 0.0,
        'training_stats': None,
        'training_log': [],

        # التحليلات
        'analytics_data': {
            'total_games': 0,
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'avg_moves': 0,
            'favorite_tile': None,
            'win_streak': 0,
            'best_streak': 0,
            'history': [],
        },
    }

    @classmethod
    def init(cls):
        """تهيئة كل المفاتيح الافتراضية"""
        for key, default_val in cls.DEFAULTS.items():
            if key not in st.session_state:
                if isinstance(default_val, (list, dict)):
                    # نسخة جديدة لتجنب المشاركة
                    import copy
                    st.session_state[key] = copy.deepcopy(
                        default_val
                    )
                else:
                    st.session_state[key] = default_val

    @classmethod
    def get(cls, key: str, default=None):
        """قراءة قيمة مع قيمة افتراضية"""
        return st.session_state.get(
            key,
            default or cls.DEFAULTS.get(key)
        )

    @classmethod
    def set(cls, key: str, value: Any):
        """تعيين قيمة"""
        st.session_state[key] = value

    @classmethod
    def reset_game(cls):
        """إعادة تعيين حالة اللعبة فقط"""
        game_keys = [
            'game_state', 'game_started', 'game_phase',
            'my_hand_input', 'selected_tile_index',
            'ai_recommendation', 'ai_analysis',
            'ai_strategy', 'ai_thinking',
            'move_history_display', 'message',
            'message_type', 'game_id',
        ]
        for key in game_keys:
            if key in cls.DEFAULTS:
                import copy
                val = cls.DEFAULTS[key]
                if isinstance(val, (list, dict)):
                    st.session_state[key] = copy.deepcopy(val)
                else:
                    st.session_state[key] = val

    @classmethod
    def reset_all(cls):
        """إعادة تعيين كل شيء"""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        cls.init()

    @classmethod
    def generate_game_id(cls) -> str:
        """توليد معرف فريد للعبة"""
        timestamp = str(time.time())
        return hashlib.md5(
            timestamp.encode()
        ).hexdigest()[:8]


# ──────────────────────────────────────────────
# مكونات الواجهة المشتركة
# ──────────────────────────────────────────────

class UIComponents:
    """
    مكونات واجهة مستخدم قابلة لإعادة الاستخدام
    """

    @staticmethod
    def metric_card(
        title: str,
        value: Union[str, int, float],
        icon: str = "📊",
        color: str = "#4CAF50",
        delta: str = "",
        width: str = "100%",
    ) -> str:
        """
        بطاقة إحصائية أنيقة

        Returns:
            HTML string
        """
        delta_html = ""
        if delta:
            delta_color = (
                "#4CAF50" if "+" in delta or "↑" in delta
                else "#F44336"
            )
            delta_html = f'''
            <div style="font-size: 12px;
                        color: {delta_color};
                        margin-top: 4px;">
                {delta}
            </div>'''

        return f'''
        <div style="
            background: linear-gradient(
                135deg,
                {color}22,
                {color}11
            );
            border: 1px solid {color}44;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            width: {width};
            transition: transform 0.3s;
        " onmouseover="this.style.transform='translateY(-3px)'"
           onmouseout="this.style.transform='translateY(0)'">
            <div style="font-size: 28px;
                        margin-bottom: 8px;">
                {icon}
            </div>
            <div style="font-size: 13px;
                        color: #999;
                        margin-bottom: 4px;">
                {title}
            </div>
            <div style="font-size: 28px;
                        font-weight: bold;
                        color: {color};">
                {value}
            </div>
            {delta_html}
        </div>'''

    @staticmethod
    def info_banner(
        message: str,
        banner_type: str = "info",
        icon: str = "",
    ) -> str:
        """
        شريط معلومات ملون

        banner_type: info, success, warning, error
        """
        configs = {
            'info': {
                'bg': 'linear-gradient(135deg, #1565C0, #1976D2)',
                'icon': icon or 'ℹ️',
            },
            'success': {
                'bg': 'linear-gradient(135deg, #2E7D32, #388E3C)',
                'icon': icon or '✅',
            },
            'warning': {
                'bg': 'linear-gradient(135deg, #E65100, #EF6C00)',
                'icon': icon or '⚠️',
            },
            'error': {
                'bg': 'linear-gradient(135deg, #B71C1C, #C62828)',
                'icon': icon or '❌',
            },
        }

        config = configs.get(banner_type, configs['info'])

        return f'''
        <div style="
            background: {config['bg']};
            border-radius: 12px;
            padding: 16px 24px;
            color: white;
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 10px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        ">
            <span style="font-size: 24px;">
                {config['icon']}
            </span>
            <span style="font-size: 15px;">
                {message}
            </span>
        </div>'''

    @staticmethod
    def progress_ring(
        percentage: float,
        label: str = "",
        size: int = 120,
        color: str = "#4CAF50",
    ) -> str:
        """
        حلقة تقدم SVG

        Args:
            percentage: 0.0 إلى 1.0
        """
        radius = size // 2 - 10
        circumference = 2 * 3.14159 * radius
        dash_offset = circumference * (1 - percentage)

        pct_text = f"{percentage * 100:.0f}%"

        return f'''
        <svg width="{size}" height="{size + 30}"
             viewBox="0 0 {size} {size + 30}">
            <!-- خلفية الحلقة -->
            <circle cx="{size // 2}" cy="{size // 2}"
                    r="{radius}"
                    fill="none"
                    stroke="#333"
                    stroke-width="8"
                    opacity="0.3"/>
            <!-- حلقة التقدم -->
            <circle cx="{size // 2}" cy="{size // 2}"
                    r="{radius}"
                    fill="none"
                    stroke="{color}"
                    stroke-width="8"
                    stroke-linecap="round"
                    stroke-dasharray="{circumference}"
                    stroke-dashoffset="{dash_offset}"
                    transform="rotate(-90 {size // 2} {size // 2})">
                <animate attributeName="stroke-dashoffset"
                         from="{circumference}"
                         to="{dash_offset}"
                         dur="1.5s" fill="freeze"/>
            </circle>
            <!-- النسبة -->
            <text x="{size // 2}" y="{size // 2 + 6}"
                  text-anchor="middle"
                  font-family="Arial"
                  font-size="20"
                  font-weight="bold"
                  fill="{color}">
                {pct_text}
            </text>
            <!-- التسمية -->
            <text x="{size // 2}" y="{size + 20}"
                  text-anchor="middle"
                  font-family="Arial"
                  font-size="12"
                  fill="#999">
                {label}
            </text>
        </svg>'''

    @staticmethod
    def tile_selector_grid(
        all_tiles: List[DominoTile],
        selected: List[DominoTile],
        disabled: List[DominoTile] = None,
        cols_per_row: int = 7,
        key_prefix: str = "sel",
    ) -> Optional[DominoTile]:
        """
        شبكة اختيار الأحجار

        Returns:
            الحجر المضغوط أو None
        """
        disabled = disabled or []
        clicked_tile = None

        for row_start in range(
            0, len(all_tiles), cols_per_row
        ):
            row = all_tiles[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)

            for idx, tile in enumerate(row):
                with cols[idx]:
                    is_sel = tile in selected
                    is_dis = tile in disabled

                    if is_sel:
                        label = f"✅ [{tile.high}|{tile.low}]"
                        btn_type = "primary"
                    elif is_dis:
                        label = f"🚫 [{tile.high}|{tile.low}]"
                        btn_type = "secondary"
                    else:
                        label = f"[{tile.high}|{tile.low}]"
                        btn_type = "secondary"

                    if st.button(
                        label,
                        key=f"{key_prefix}_{tile.high}_{tile.low}",
                        use_container_width=True,
                        type=btn_type,
                        disabled=is_dis,
                    ):
                        clicked_tile = tile

        return clicked_tile

    @staticmethod
    def animated_counter(
        value: int,
        label: str,
        icon: str = "",
    ) -> str:
        """عداد متحرك"""
        return f'''
        <div style="text-align: center; padding: 10px;">
            <div style="font-size: 36px;">{icon}</div>
            <div style="font-size: 42px;
                        font-weight: bold;
                        color: #4CAF50;
                        font-family: monospace;">
                {value:,}
            </div>
            <div style="font-size: 13px;
                        color: #888;
                        margin-top: 4px;">
                {label}
            </div>
        </div>'''


# ──────────────────────────────────────────────
# حفظ وتحميل اللعبة
# ──────────────────────────────────────────────

class GameSaveManager:
    """
    حفظ وتحميل حالة اللعبة
    """

    SAVE_DIR = "saves"

    @classmethod
    def _ensure_dir(cls):
        os.makedirs(cls.SAVE_DIR, exist_ok=True)

    @classmethod
    def save_game(
        cls,
        state: GameState,
        name: str = ""
    ) -> str:
        """
        حفظ اللعبة كملف JSON

        Returns:
            مسار الملف المحفوظ
        """
        cls._ensure_dir()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_{name or timestamp}.json"
        filepath = os.path.join(cls.SAVE_DIR, filename)

        data = {
            'version': APP_VERSION,
            'timestamp': timestamp,
            'name': name,

            # الطاولة
            'board': {
                'left_end': state.board.left_end,
                'right_end': state.board.right_end,
                'tiles_played': [
                    {
                        'high': t.high,
                        'low': t.low,
                        'direction': d.value
                    }
                    for t, d in state.board.tiles_played
                ],
            },

            # اللاعبون
            'players': {},
            'current_turn': state.current_turn.value,
            'consecutive_passes': state.consecutive_passes,
            'is_game_over': state.is_game_over,
            'winner': (
                state.winner.value
                if state.winner else None
            ),

            # السجل
            'move_history': [
                {
                    'player': m.player.value,
                    'tile': (
                        {'high': m.tile.high, 'low': m.tile.low}
                        if m.tile else None
                    ),
                    'direction': (
                        m.direction.value
                        if m.direction else None
                    ),
                }
                for m in state.move_history
            ],
        }

        # بيانات اللاعبين
        for pos, player in state.players.items():
            data['players'][str(pos.value)] = {
                'hand': [
                    {'high': t.high, 'low': t.low}
                    for t in player.hand
                ],
                'tiles_count': player.tiles_count,
                'passed_values': list(player.passed_values),
                'played_tiles': [
                    {'high': t.high, 'low': t.low}
                    for t in player.played_tiles
                ],
                'is_me': player.is_me,
            }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    @classmethod
    def load_game(cls, filepath: str) -> Optional[GameState]:
        """تحميل لعبة محفوظة"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            state = GameState()
            state.initialize_players()

            # الطاولة
            board_data = data['board']
            state.board.left_end = board_data['left_end']
            state.board.right_end = board_data['right_end']

            for tp in board_data['tiles_played']:
                tile = DominoTile(tp['high'], tp['low'])
                direction = Direction(tp['direction'])
                state.board.tiles_played.append(
                    (tile, direction)
                )

            # اللاعبون
            for pos_str, pdata in data['players'].items():
                pos = PlayerPosition(int(pos_str))
                player = state.players[pos]

                player.hand = [
                    DominoTile(t['high'], t['low'])
                    for t in pdata['hand']
                ]
                player.tiles_count = pdata['tiles_count']
                player.passed_values = set(
                    pdata['passed_values']
                )
                player.played_tiles = [
                    DominoTile(t['high'], t['low'])
                    for t in pdata['played_tiles']
                ]
                player.is_me = pdata['is_me']

            state.current_turn = PlayerPosition(
                data['current_turn']
            )
            state.consecutive_passes = data[
                'consecutive_passes'
            ]
            state.is_game_over = data['is_game_over']

            if data['winner'] is not None:
                state.winner = PlayerPosition(data['winner'])

            # السجل
            for mdata in data['move_history']:
                tile = None
                direction = None
                if mdata['tile']:
                    tile = DominoTile(
                        mdata['tile']['high'],
                        mdata['tile']['low']
                    )
                if mdata['direction']:
                    direction = Direction(mdata['direction'])

                move = Move(
                    PlayerPosition(mdata['player']),
                    tile,
                    direction,
                )
                state.move_history.append(move)

            return state

        except Exception as e:
            st.error(f"خطأ في تحميل اللعبة: {e}")
            return None

    @classmethod
    def list_saves(cls) -> List[Dict]:
        """عرض الألعاب المحفوظة"""
        cls._ensure_dir()

        saves = []
        save_path = Path(cls.SAVE_DIR)

        for f in sorted(
            save_path.glob("game_*.json"),
            reverse=True
        ):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)

                saves.append({
                    'filepath': str(f),
                    'filename': f.name,
                    'name': data.get('name', ''),
                    'timestamp': data.get('timestamp', ''),
                    'is_over': data.get('is_game_over', False),
                    'moves': len(data.get('move_history', [])),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return saves

    @classmethod
    def delete_save(cls, filepath: str) -> bool:
        """حذف لعبة محفوظة"""
        try:
            os.remove(filepath)
            return True
        except OSError:
            return False

    @classmethod
    def export_game_json(cls, state: GameState) -> str:
        """تصدير اللعبة كنص JSON (للتنزيل)"""
        filepath = cls.save_game(state, "export_temp")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        os.remove(filepath)
        return content


# ──────────────────────────────────────────────
# إحصائيات اللاعب
# ──────────────────────────────────────────────

class PlayerStats:
    """
    تتبع إحصائيات اللاعب عبر الجلسات
    """

    @classmethod
    def _load(cls) -> Dict:
        """تحميل الإحصائيات"""
        if os.path.exists(STATS_FILE):
            try:
                with open(
                    STATS_FILE, 'r', encoding='utf-8'
                ) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            'total_games': 0,
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'dominos': 0,
            'locks': 0,
            'total_moves': 0,
            'total_points_won': 0,
            'total_points_lost': 0,
            'best_streak': 0,
            'current_streak': 0,
            'tiles_played': {},
            'favorite_openings': {},
            'ai_accuracy': [],
            'game_durations': [],
            'game_history': [],
        }

    @classmethod
    def _save(cls, stats: Dict):
        """حفظ الإحصائيات"""
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    @classmethod
    def record_game(
        cls,
        result: str,
        moves_count: int,
        points_won: int = 0,
        points_lost: int = 0,
        duration: float = 0,
        tiles_played: List[DominoTile] = None,
    ):
        """تسجيل نتيجة مباراة"""
        stats = cls._load()

        stats['total_games'] += 1
        stats['total_moves'] += moves_count
        stats['total_points_won'] += points_won
        stats['total_points_lost'] += points_lost

        if duration > 0:
            stats['game_durations'].append(round(duration, 1))

        if result == 'win':
            stats['wins'] += 1
            stats['current_streak'] += 1
            stats['best_streak'] = max(
                stats['best_streak'],
                stats['current_streak']
            )
        elif result == 'loss':
            stats['losses'] += 1
            stats['current_streak'] = 0
        else:
            stats['draws'] += 1

        # تسجيل الأحجار
        if tiles_played:
            for tile in tiles_played:
                key = f"{tile.high}-{tile.low}"
                stats['tiles_played'][key] = (
                    stats['tiles_played'].get(key, 0) + 1
                )

        # سجل اللعبة
        stats['game_history'].append({
            'date': datetime.now().isoformat(),
            'result': result,
            'moves': moves_count,
            'points_won': points_won,
            'points_lost': points_lost,
        })

        # نحتفظ بآخر 100 لعبة
        stats['game_history'] = stats['game_history'][-100:]
        stats['game_durations'] = stats['game_durations'][-100:]

        cls._save(stats)

    @classmethod
    def get_stats(cls) -> Dict:
        """الحصول على الإحصائيات"""
        return cls._load()

    @classmethod
    def get_win_rate(cls) -> float:
        """نسبة الفوز"""
        stats = cls._load()
        total = stats['total_games']
        if total == 0:
            return 0.0
        return stats['wins'] / total

    @classmethod
    def get_favorite_tile(cls) -> Optional[str]:
        """الحجر المفضل"""
        stats = cls._load()
        tiles = stats.get('tiles_played', {})
        if not tiles:
            return None
        return max(tiles, key=tiles.get)

    @classmethod
    def reset(cls):
        """مسح الإحصائيات"""
        if os.path.exists(STATS_FILE):
            os.remove(STATS_FILE)


# ──────────────────────────────────────────────
# أدوات التنسيق والتحويل
# ──────────────────────────────────────────────

class Formatter:
    """أدوات التنسيق"""

    @staticmethod
    def format_duration(seconds: float) -> str:
        """تنسيق المدة"""
        if seconds < 60:
            return f"{seconds:.1f} ثانية"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes} دقيقة و {secs} ثانية"

    @staticmethod
    def format_number(num: int) -> str:
        """تنسيق الأرقام الكبيرة"""
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)

    @staticmethod
    def format_percentage(value: float) -> str:
        """تنسيق النسبة المئوية"""
        return f"{value * 100:.1f}%"

    @staticmethod
    def move_to_text(move: Move) -> str:
        """تحويل حركة لنص"""
        name = PLAYER_NAMES.get(
            move.player, str(move.player)
        )
        icon = PLAYER_ICONS.get(move.player, "⚪")

        if move.is_pass:
            return f"{icon} {name}: دق 🚫"

        dir_text = (
            "⬅️ يسار"
            if move.direction == Direction.LEFT
            else "➡️ يمين"
        )
        return (
            f"{icon} {name}: "
            f"[{move.tile.high}|{move.tile.low}] "
            f"{dir_text}"
        )

    @staticmethod
    def tile_to_emoji(tile: DominoTile) -> str:
        """تحويل حجر لإيموجي"""
        pip_emoji = {
            0: "⬜", 1: "1️⃣", 2: "2️⃣",
            3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
        }
        h = pip_emoji.get(tile.high, "?")
        l = pip_emoji.get(tile.low, "?")
        return f"[{h}|{l}]"

    @staticmethod
    def confidence_badge(win_rate: float) -> str:
        """شارة الثقة"""
        if win_rate >= 0.75:
            return "🟢 ممتاز"
        elif win_rate >= 0.55:
            return "🟡 جيد"
        elif win_rate >= 0.40:
            return "🟠 متوسط"
        return "🔴 ضعيف"


# ──────────────────────────────────────────────
# أدوات التصدير
# ──────────────────────────────────────────────

class ExportTools:
    """أدوات تصدير البيانات والصور"""

    @staticmethod
    def svg_to_download_link(
        svg_content: str,
        filename: str = "domino.svg",
        link_text: str = "تنزيل SVG",
    ) -> str:
        """تحويل SVG لرابط تنزيل"""
        b64 = base64.b64encode(
            svg_content.encode('utf-8')
        ).decode()

        return (
            f'<a href="data:image/svg+xml;base64,{b64}" '
            f'download="{filename}" '
            f'style="text-decoration:none; '
            f'color: #4CAF50; font-weight: bold;">'
            f'📥 {link_text}</a>'
        )

    @staticmethod
    def json_to_download_link(
        json_content: str,
        filename: str = "game.json",
        link_text: str = "تنزيل JSON",
    ) -> str:
        """تحويل JSON لرابط تنزيل"""
        b64 = base64.b64encode(
            json_content.encode('utf-8')
        ).decode()

        return (
            f'<a href="data:application/json;base64,{b64}" '
            f'download="{filename}" '
            f'style="text-decoration:none; '
            f'color: #2196F3; font-weight: bold;">'
            f'📥 {link_text}</a>'
        )

    @staticmethod
    def generate_game_report(
        state: GameState,
        analysis: Dict = None,
    ) -> str:
        """
        توليد تقرير كامل عن اللعبة
        """
        lines = [
            f"# تقرير لعبة الدومينو",
            f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"",
            f"## حالة الطاولة",
            f"الطرف الأيسر: {state.board.left_end}",
            f"الطرف الأيمن: {state.board.right_end}",
            f"عدد الأحجار على الطاولة: {len(state.board.tiles_played)}",
            f"",
            f"## اللاعبون",
        ]

        for pos, player in state.players.items():
            name = PLAYER_NAMES.get(pos, str(pos))
            lines.append(f"### {name}")
            lines.append(
                f"- أحجار متبقية: {player.tiles_count}"
            )
            if player.passed_values:
                passed = ", ".join(
                    str(v) for v in player.passed_values
                )
                lines.append(f"- دق على: {passed}")

        lines.extend([
            f"",
            f"## سجل الحركات ({len(state.move_history)} حركة)",
        ])

        for i, move in enumerate(state.move_history, 1):
            lines.append(
                f"{i}. {Formatter.move_to_text(move)}"
            )

        if analysis:
            lines.extend([
                f"",
                f"## تحليل الذكاء الاصطناعي",
                f"- محاكاات: {analysis.get('total_simulations', 0)}",
                f"- وقت التحليل: {analysis.get('time_elapsed', '')}",
            ])

        return "\n".join(lines)


# ──────────────────────────────────────────────
# مدير الإشعارات
# ──────────────────────────────────────────────

class NotificationManager:
    """إدارة الإشعارات والرسائل"""

    @staticmethod
    def show_toast(
        message: str,
        toast_type: str = "info",
        duration: int = 3,
    ):
        """عرض إشعار مؤقت"""
        st.toast(message, icon={
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
        }.get(toast_type, 'ℹ️'))

    @staticmethod
    def show_message(
        message: str,
        msg_type: str = "info"
    ):
        """عرض رسالة ثابتة"""
        func = {
            'info': st.info,
            'success': st.success,
            'warning': st.warning,
            'error': st.error,
        }.get(msg_type, st.info)
        func(message)

    @staticmethod
    def show_banner(message: str, banner_type: str = "info"):
        """عرض شريط معلومات HTML"""
        html = UIComponents.info_banner(
            message, banner_type
        )
        st.markdown(html, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# أدوات CSS
# ──────────────────────────────────────────────

class StyleManager:
    """إدارة الأنماط"""

    @staticmethod
    def load_css(filepath: str = "assets/style.css"):
        """تحميل ملف CSS"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                css = f.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    @staticmethod
    def inject_css(css: str):
        """حقن CSS مباشر"""
        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True
        )

    @staticmethod
    def get_theme_css(theme: TileTheme) -> str:
        """CSS حسب السمة"""
        colors = {
            TileTheme.MODERN: {
                'primary': '#2196F3',
                'bg': '#1a1a2e',
                'card': 'rgba(255,255,255,0.05)',
            },
            TileTheme.DARK: {
                'primary': '#BB86FC',
                'bg': '#121212',
                'card': 'rgba(255,255,255,0.08)',
            },
            TileTheme.CLASSIC: {
                'primary': '#4CAF50',
                'bg': '#1B5E20',
                'card': 'rgba(255,255,255,0.1)',
            },
            TileTheme.WOODEN: {
                'primary': '#8D6E63',
                'bg': '#3E2723',
                'card': 'rgba(255,255,255,0.07)',
            },
        }

        c = colors.get(theme, colors[TileTheme.MODERN])

        return f"""
        .stApp {{
            background: {c['bg']};
        }}
        .game-card {{
            background: {c['card']};
            border: 1px solid {c['primary']}33;
        }}
        """


# ──────────────────────────────────────────────
# توليد كل الأحجار الممكنة
# ──────────────────────────────────────────────

def generate_all_tiles(max_pip: int = 6) -> List[DominoTile]:
    """توليد كل 28 حجر مرتبة"""
    tiles = []
    for i in range(max_pip + 1):
        for j in range(i, max_pip + 1):
            tiles.append(DominoTile(j, i))
    return tiles


def get_playable_tiles(
    hand: List[DominoTile],
    board: Board,
) -> List[int]:
    """
    فهارس الأحجار القابلة للعب من اليد

    Returns:
        قائمة فهارس
    """
    if board.is_empty:
        return list(range(len(hand)))

    indices = []
    for i, tile in enumerate(hand):
        if board.can_play(tile):
            indices.append(i)
    return indices
