# svg_renderer.py
"""
محرك رسم أحجار الدومينو بـ SVG
كل حجر يُرسم كـ SVG نظيف وقابل للتكبير

الميزات:
  - رسم حجر واحد
  - رسم يد كاملة
  - رسم الطاولة
  - رسم خريطة اللاعبين
  - ألوان وتأثيرات متعددة
"""

from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from enum import Enum

# نستورد من محرك اللعبة
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo
)


# ──────────────────────────────────────────────
# إعدادات الرسم
# ──────────────────────────────────────────────

class TileTheme(Enum):
    """سمات الألوان"""
    CLASSIC = "classic"
    DARK = "dark"
    MODERN = "modern"
    WOODEN = "wooden"


@dataclass
class ThemeColors:
    """ألوان السمة"""
    tile_bg: str = "#FFFFFF"
    tile_border: str = "#333333"
    tile_divider: str = "#999999"
    pip_color: str = "#1a1a1a"
    pip_double: str = "#CC0000"
    highlight_bg: str = "#E8F5E9"
    highlight_border: str = "#4CAF50"
    shadow: str = "rgba(0,0,0,0.15)"
    text_color: str = "#333333"
    board_bg: str = "#2E7D32"
    player_friendly: str = "#1565C0"
    player_enemy: str = "#C62828"


THEMES = {
    TileTheme.CLASSIC: ThemeColors(),
    TileTheme.DARK: ThemeColors(
        tile_bg="#2D2D2D",
        tile_border="#555555",
        tile_divider="#666666",
        pip_color="#FFFFFF",
        pip_double="#FF6B6B",
        highlight_bg="#1B5E20",
        highlight_border="#66BB6A",
        shadow="rgba(0,0,0,0.3)",
        text_color="#EEEEEE",
        board_bg="#1B3A1B",
        player_friendly="#42A5F5",
        player_enemy="#EF5350",
    ),
    TileTheme.MODERN: ThemeColors(
        tile_bg="#F5F5F5",
        tile_border="#78909C",
        tile_divider="#B0BEC5",
        pip_color="#263238",
        pip_double="#E91E63",
        highlight_bg="#E3F2FD",
        highlight_border="#2196F3",
        shadow="rgba(0,0,0,0.1)",
        text_color="#37474F",
        board_bg="#37474F",
        player_friendly="#29B6F6",
        player_enemy="#FF7043",
    ),
    TileTheme.WOODEN: ThemeColors(
        tile_bg="#FFF8E1",
        tile_border="#5D4037",
        tile_divider="#8D6E63",
        pip_color="#3E2723",
        pip_double="#BF360C",
        highlight_bg="#E8F5E9",
        highlight_border="#66BB6A",
        shadow="rgba(0,0,0,0.2)",
        text_color="#4E342E",
        board_bg="#33691E",
        player_friendly="#0277BD",
        player_enemy="#AD1457",
    ),
}


# ──────────────────────────────────────────────
# مواقع النقاط على حجر الدومينو
# ──────────────────────────────────────────────

# نقاط الدومينو في شبكة 3×3
# كل موقع = (نسبة X, نسبة Y) من حجم النصف
PIP_POSITIONS = {
    0: [],
    1: [(0.5, 0.5)],
    2: [(0.25, 0.75), (0.75, 0.25)],
    3: [(0.25, 0.75), (0.5, 0.5), (0.75, 0.25)],
    4: [
        (0.25, 0.25), (0.25, 0.75),
        (0.75, 0.25), (0.75, 0.75)
    ],
    5: [
        (0.25, 0.25), (0.25, 0.75),
        (0.5, 0.5),
        (0.75, 0.25), (0.75, 0.75)
    ],
    6: [
        (0.25, 0.25), (0.25, 0.5), (0.25, 0.75),
        (0.75, 0.25), (0.75, 0.5), (0.75, 0.75)
    ],
}


# ──────────────────────────────────────────────
# رسم SVG
# ──────────────────────────────────────────────

class DominoSVG:
    """
    رسم أحجار الدومينو كـ SVG
    """

    def __init__(
        self,
        theme: TileTheme = TileTheme.MODERN,
        tile_width: int = 120,
        tile_height: int = 60,
        pip_radius: int = 7,
        corner_radius: int = 8,
        spacing: int = 10,
    ):
        self.colors = THEMES.get(theme, THEMES[TileTheme.MODERN])
        self.tile_w = tile_width
        self.tile_h = tile_height
        self.pip_r = pip_radius
        self.corner_r = corner_radius
        self.spacing = spacing
        self.half_w = tile_width // 2

    # ──────────────────────────────────────
    # SVG Definitions (فلاتر وتدرجات)
    # ──────────────────────────────────────

    def _svg_defs(self) -> str:
        """تعريفات SVG مشتركة: ظل + تدرج"""
        return f'''
  <defs>
    <filter id="shadow" x="-10%" y="-10%"
            width="130%" height="130%">
      <feDropShadow dx="2" dy="2" stdDeviation="3"
        flood-color="{self.colors.shadow}" />
    </filter>
    <filter id="shadow-sm" x="-5%" y="-5%"
            width="115%" height="115%">
      <feDropShadow dx="1" dy="1" stdDeviation="1.5"
        flood-color="{self.colors.shadow}" />
    </filter>
    <linearGradient id="tileGrad" x1="0" y1="0"
                    x2="0" y2="1">
      <stop offset="0%" stop-color="{self.colors.tile_bg}"
            stop-opacity="1"/>
      <stop offset="100%"
            stop-color="{self._darken(self.colors.tile_bg, 0.05)}"
            stop-opacity="1"/>
    </linearGradient>
    <linearGradient id="highlightGrad" x1="0" y1="0"
                    x2="0" y2="1">
      <stop offset="0%"
            stop-color="{self.colors.highlight_bg}"
            stop-opacity="1"/>
      <stop offset="100%"
            stop-color="{self._darken(self.colors.highlight_bg, 0.08)}"
            stop-opacity="1"/>
    </linearGradient>
  </defs>'''

    # ──────────────────────────────────────
    # رسم حجر واحد
    # ──────────────────────────────────────

    def render_tile(
        self,
        tile: DominoTile,
        x: int = 0,
        y: int = 0,
        highlighted: bool = False,
        selected: bool = False,
        show_label: bool = False,
        label: str = "",
        horizontal: bool = True,
        clickable: bool = False,
        tile_id: str = "",
    ) -> str:
        """
        رسم حجر دومينو واحد كـ SVG

        Args:
            tile: الحجر
            x, y: الموقع
            highlighted: تمييز (أخضر)
            selected: محدد (حدود سميكة)
            show_label: عرض تسمية تحت الحجر
            label: نص التسمية
            horizontal: أفقي أو عمودي
            clickable: قابل للنقر
            tile_id: معرّف فريد
        """
        w = self.tile_w if horizontal else self.tile_h
        h = self.tile_h if horizontal else self.tile_w

        # ألوان
        fill = (
            "url(#highlightGrad)" if highlighted
            else "url(#tileGrad)"
        )
        stroke = (
            self.colors.highlight_border if highlighted
            else self.colors.tile_border
        )
        stroke_w = 3 if selected else 2

        # بداية المجموعة
        cursor = ' style="cursor:pointer"' if clickable else ''
        data_attr = f' data-tile="{tile_id}"' if tile_id else ''

        svg = f'''
  <g transform="translate({x},{y})"{cursor}{data_attr}
     class="domino-tile">
    <!-- جسم الحجر -->
    <rect x="0" y="0" width="{w}" height="{h}"
          rx="{self.corner_r}" ry="{self.corner_r}"
          fill="{fill}" stroke="{stroke}"
          stroke-width="{stroke_w}"
          filter="url(#shadow-sm)"/>'''

        if horizontal:
            # خط فاصل عمودي
            mid_x = w // 2
            svg += f'''
    <line x1="{mid_x}" y1="4" x2="{mid_x}" y2="{h - 4}"
          stroke="{self.colors.tile_divider}"
          stroke-width="1.5"
          stroke-dasharray="2,2"/>'''

            # نقاط النصف الأيسر (high)
            svg += self._render_pips(
                tile.high, 0, 0,
                self.half_w, h,
                tile.is_double
            )
            # نقاط النصف الأيمن (low)
            svg += self._render_pips(
                tile.low, self.half_w, 0,
                self.half_w, h,
                tile.is_double
            )
        else:
            # خط فاصل أفقي (عمودي)
            mid_y = h // 2
            svg += f'''
    <line x1="4" y1="{mid_y}" x2="{w - 4}" y2="{mid_y}"
          stroke="{self.colors.tile_divider}"
          stroke-width="1.5"
          stroke-dasharray="2,2"/>'''

            svg += self._render_pips(
                tile.high, 0, 0,
                w, h // 2,
                tile.is_double
            )
            svg += self._render_pips(
                tile.low, 0, h // 2,
                w, h // 2,
                tile.is_double
            )

        # تسمية
        if show_label and label:
            label_y = h + 18 if horizontal else h + 18
            svg += f'''
    <text x="{w // 2}" y="{label_y}"
          text-anchor="middle"
          font-family="Arial, sans-serif"
          font-size="12"
          fill="{self.colors.text_color}"
          font-weight="bold">{label}</text>'''

        # تأثير hover
        if clickable:
            svg += f'''
    <rect x="0" y="0" width="{w}" height="{h}"
          rx="{self.corner_r}" ry="{self.corner_r}"
          fill="transparent" stroke="transparent"
          stroke-width="3" class="hover-rect">
      <animate attributeName="stroke"
               values="transparent;{self.colors.highlight_border};transparent"
               dur="2s" repeatCount="indefinite"/>
    </rect>'''

        svg += '\n  </g>'
        return svg

    def _render_pips(
        self,
        count: int,
        offset_x: int,
        offset_y: int,
        area_w: int,
        area_h: int,
        is_double: bool = False,
    ) -> str:
        """رسم النقاط في منطقة محددة"""
        positions = PIP_POSITIONS.get(count, [])
        color = (
            self.colors.pip_double if is_double
            else self.colors.pip_color
        )

        svg = ""
        padding = 8

        for px, py in positions:
            cx = offset_x + padding + px * (area_w - 2 * padding)
            cy = offset_y + padding + py * (area_h - 2 * padding)

            svg += f'''
    <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{self.pip_r}"
            fill="{color}">
      <animate attributeName="r"
               values="{self.pip_r};{self.pip_r + 0.3};{self.pip_r}"
               dur="3s" repeatCount="indefinite"/>
    </circle>'''

        return svg

    # ──────────────────────────────────────
    # رسم يد اللاعب
    # ──────────────────────────────────────

    def render_hand(
        self,
        tiles: List[DominoTile],
        highlighted_indices: List[int] = None,
        selected_index: int = -1,
        show_numbers: bool = True,
        clickable: bool = True,
        title: str = "يدك",
    ) -> str:
        """
        رسم يد كاملة (مجموعة أحجار)
        """
        highlighted_indices = highlighted_indices or []
        n = len(tiles)

        if n == 0:
            return self._empty_hand_svg(title)

        total_w = n * (self.tile_w + self.spacing) + 40
        total_h = self.tile_h + 60

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {total_w} {total_h}"
     width="100%" height="{total_h}">
{self._svg_defs()}

  <!-- عنوان -->
  <text x="{total_w // 2}" y="15"
        text-anchor="middle"
        font-family="Arial, sans-serif"
        font-size="14" font-weight="bold"
        fill="{self.colors.text_color}">
    🃏 {title} ({n} أحجار)
  </text>
'''

        for i, tile in enumerate(tiles):
            tx = 20 + i * (self.tile_w + self.spacing)
            ty = 25

            is_high = i in highlighted_indices
            is_sel = i == selected_index
            lbl = f"({i + 1})" if show_numbers else ""

            svg += self.render_tile(
                tile,
                x=tx, y=ty,
                highlighted=is_high,
                selected=is_sel,
                show_label=show_numbers,
                label=lbl,
                clickable=clickable,
                tile_id=f"{tile.high}-{tile.low}",
            )

        # مجموع النقاط
        total_pts = sum(t.total for t in tiles)
        svg += f'''
  <text x="{total_w // 2}" y="{total_h - 5}"
        text-anchor="middle"
        font-family="Arial, sans-serif"
        font-size="11"
        fill="{self.colors.text_color}"
        opacity="0.7">
    مجموع النقاط: {total_pts}
  </text>
</svg>'''

        return svg

    def _empty_hand_svg(self, title: str) -> str:
        return f'''<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 300 80" width="300" height="80">
  <rect x="10" y="10" width="280" height="60"
        rx="10" fill="#f0f0f0" stroke="#ccc"
        stroke-dasharray="5,5"/>
  <text x="150" y="45" text-anchor="middle"
        font-family="Arial" font-size="14"
        fill="#999">
    {title} - فارغة 🎯
  </text>
</svg>'''

    # ──────────────────────────────────────
    # رسم الطاولة
    # ──────────────────────────────────────

    def render_board(
        self,
        board: Board,
        width: int = 800,
        height: int = 200,
    ) -> str:
        """
        رسم الطاولة مع كل الأحجار الملعوبة
        """
        if board.is_empty:
            return self._empty_board_svg(width, height)

        played = board.all_played_tiles
        n = len(played)
        tile_total_w = self.tile_w + self.spacing

        # حساب العرض الفعلي
        chain_w = n * tile_total_w + 40
        actual_w = max(width, chain_w)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {actual_w} {height}"
     width="100%" height="{height}">
{self._svg_defs()}

  <!-- خلفية الطاولة -->
  <rect x="0" y="0" width="{actual_w}" height="{height}"
        rx="12" fill="{self.colors.board_bg}"
        opacity="0.9"/>

  <!-- نمط اللباد -->
  <pattern id="felt" x="0" y="0"
           width="20" height="20"
           patternUnits="userSpaceOnUse">
    <rect width="20" height="20"
          fill="{self.colors.board_bg}"/>
    <circle cx="10" cy="10" r="0.5"
            fill="rgba(255,255,255,0.05)"/>
  </pattern>
  <rect x="0" y="0" width="{actual_w}" height="{height}"
        rx="12" fill="url(#felt)"/>

  <!-- خط السلسلة -->
  <line x1="20" y1="{height // 2}"
        x2="{actual_w - 20}" y2="{height // 2}"
        stroke="rgba(255,255,255,0.15)"
        stroke-width="2"
        stroke-dasharray="8,4"/>
'''

        # رسم الأحجار
        start_x = max(
            20,
            (actual_w - n * tile_total_w) // 2
        )

        for i, tile in enumerate(played):
            tx = start_x + i * tile_total_w
            ty = (height - self.tile_h) // 2

            svg += self.render_tile(
                tile, x=tx, y=ty,
                horizontal=True
            )

        # الأطراف
        svg += f'''
  <!-- الأطراف المفتوحة -->
  <g transform="translate(8, {height // 2 - 15})">
    <rect x="0" y="0" width="30" height="30"
          rx="6" fill="rgba(255,255,255,0.2)"/>
    <text x="15" y="22" text-anchor="middle"
          font-family="Arial" font-size="18"
          font-weight="bold" fill="white">
      {board.left_end}
    </text>
  </g>
  <g transform="translate({actual_w - 38}, {height // 2 - 15})">
    <rect x="0" y="0" width="30" height="30"
          rx="6" fill="rgba(255,255,255,0.2)"/>
    <text x="15" y="22" text-anchor="middle"
          font-family="Arial" font-size="18"
          font-weight="bold" fill="white">
      {board.right_end}
    </text>
  </g>

  <!-- تسميات الأطراف -->
  <text x="23" y="{height - 8}"
        text-anchor="middle"
        font-size="9" fill="rgba(255,255,255,0.5)">
    يسار
  </text>
  <text x="{actual_w - 23}" y="{height - 8}"
        text-anchor="middle"
        font-size="9" fill="rgba(255,255,255,0.5)">
    يمين
  </text>

</svg>'''

        return svg

    def _empty_board_svg(self, w: int, h: int) -> str:
        return f'''<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <rect x="0" y="0" width="{w}" height="{h}"
        rx="12" fill="{self.colors.board_bg}"
        opacity="0.8"/>
  <text x="{w // 2}" y="{h // 2 + 5}"
        text-anchor="middle"
        font-family="Arial" font-size="16"
        fill="rgba(255,255,255,0.6)">
    🎲 الطاولة فارغة - في انتظار أول حجر
  </text>
</svg>'''

    # ──────────────────────────────────────
    # رسم خريطة اللاعبين
    # ──────────────────────────────────────

    def render_players_map(
        self,
        state: GameState,
        width: int = 700,
        height: int = 500,
    ) -> str:
        """
        خريطة اللاعبين حول الطاولة
        """
        cx, cy = width // 2, height // 2

        positions_xy = {
            PlayerPosition.SOUTH: (cx, height - 60),
            PlayerPosition.NORTH: (cx, 60),
            PlayerPosition.WEST:  (70, cy),
            PlayerPosition.EAST:  (width - 70, cy),
        }

        labels = {
            PlayerPosition.SOUTH: "أنت 🟢",
            PlayerPosition.NORTH: "شريكك 🔵",
            PlayerPosition.WEST:  "خصم ←",
            PlayerPosition.EAST:  "→ خصم",
        }

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {width} {height}"
     width="100%" height="{height}">
{self._svg_defs()}

  <!-- طاولة مركزية -->
  <ellipse cx="{cx}" cy="{cy}"
           rx="{width // 3}" ry="{height // 4}"
           fill="{self.colors.board_bg}"
           opacity="0.3" stroke="{self.colors.board_bg}"
           stroke-width="2"/>
  <text x="{cx}" y="{cy + 5}" text-anchor="middle"
        font-size="14" fill="{self.colors.text_color}"
        opacity="0.5">
    🎲 الطاولة
  </text>
'''

        for pos in PlayerPosition:
            player = state.players[pos]
            px, py = positions_xy[pos]
            label = labels[pos]
            is_current = (pos == state.current_turn)

            is_friendly = pos in (
                PlayerPosition.SOUTH,
                PlayerPosition.NORTH
            )
            color = (
                self.colors.player_friendly if is_friendly
                else self.colors.player_enemy
            )

            # مربع اللاعب
            box_w, box_h = 130, 80
            bx = px - box_w // 2
            by = py - box_h // 2

            border_w = 3 if is_current else 1.5
            glow = (
                f'filter="url(#shadow)"'
                if is_current else ''
            )

            svg += f'''
  <g {glow}>
    <rect x="{bx}" y="{by}"
          width="{box_w}" height="{box_h}"
          rx="10" fill="white" fill-opacity="0.9"
          stroke="{color}"
          stroke-width="{border_w}"/>
'''

            # شريط ملون علوي
            svg += f'''
    <rect x="{bx}" y="{by}"
          width="{box_w}" height="24"
          rx="10" fill="{color}" opacity="0.9"/>
    <rect x="{bx}" y="{by + 14}"
          width="{box_w}" height="10"
          fill="{color}" opacity="0.9"/>
'''

            # اسم اللاعب
            svg += f'''
    <text x="{px}" y="{by + 17}"
          text-anchor="middle"
          font-family="Arial" font-size="12"
          font-weight="bold" fill="white">
      {label}
    </text>
'''

            # عدد الأحجار
            tiles_count = (
                len(player.hand) if player.is_me
                else player.tiles_count
            )
            tiles_icons = "🀫 " * min(tiles_count, 7)

            svg += f'''
    <text x="{px}" y="{by + 42}"
          text-anchor="middle"
          font-family="Arial" font-size="11"
          fill="{self.colors.text_color}">
      أحجار: {tiles_count}
    </text>
    <text x="{px}" y="{by + 58}"
          text-anchor="middle"
          font-size="10">
      {tiles_icons}
    </text>
'''

            # أرقام مدقوقة
            if player.passed_values:
                passed_str = ",".join(
                    str(v) for v in sorted(player.passed_values)
                )
                svg += f'''
    <text x="{px}" y="{by + 73}"
          text-anchor="middle"
          font-size="9"
          fill="{self.colors.player_enemy}"
          opacity="0.8">
      🚫 دق: {passed_str}
    </text>
'''

            # مؤشر الدور
            if is_current:
                svg += f'''
    <circle cx="{bx + box_w - 8}" cy="{by + 8}"
            r="5" fill="#4CAF50">
      <animate attributeName="opacity"
               values="1;0.3;1" dur="1.5s"
               repeatCount="indefinite"/>
    </circle>
'''

            svg += '  </g>\n'

        svg += '</svg>'
        return svg

    # ──────────────────────────────────────
    # رسم تحليل الحركات
    # ──────────────────────────────────────

    def render_move_analysis(
        self,
        moves_data: List[Dict],
        width: int = 600,
    ) -> str:
        """
        رسم بياني لتحليل الحركات من MCTS
        """
        if not moves_data:
            return ""

        bar_height = 35
        padding = 20
        n = min(len(moves_data), 6)
        total_h = n * (bar_height + 10) + 60

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {width} {total_h}"
     width="100%" height="{total_h}">

  <text x="{width // 2}" y="20"
        text-anchor="middle"
        font-family="Arial" font-size="14"
        font-weight="bold"
        fill="{self.colors.text_color}">
    📊 تحليل الخيارات
  </text>
'''

        max_visits = max(
            m.get('visits', 1) for m in moves_data[:n]
        )

        rank_icons = ["🥇", "🥈", "🥉", "4⃣", "5⃣", "6⃣"]
        bar_colors = [
            "#4CAF50", "#8BC34A", "#FFC107",
            "#FF9800", "#FF5722", "#9E9E9E"
        ]

        for i, md in enumerate(moves_data[:n]):
            y = 35 + i * (bar_height + 10)
            win_rate_str = md.get('win_rate', '0%')

            # تحويل نسبة الفوز لرقم
            try:
                win_pct = float(win_rate_str.strip('%')) / 100
            except (ValueError, AttributeError):
                win_pct = 0.0

            bar_w = max(
                10,
                int((width - 180) * win_pct)
            )

            visits = md.get('visits', 0)
            visits_ratio = visits / max_visits if max_visits else 0

            icon = rank_icons[i] if i < len(rank_icons) else ""
            color = bar_colors[i] if i < len(bar_colors) else "#9E9E9E"

            svg += f'''
  <g transform="translate({padding}, {y})">
    <!-- ترتيب -->
    <text x="0" y="22" font-size="16">{icon}</text>

    <!-- اسم الحركة -->
    <text x="30" y="15" font-family="Arial"
          font-size="11" fill="{self.colors.text_color}">
      {md.get('move', '?')}
    </text>

    <!-- شريط النسبة -->
    <rect x="30" y="20" width="{width - 180}"
          height="12" rx="6"
          fill="#EEEEEE"/>
    <rect x="30" y="20" width="{bar_w}"
          height="12" rx="6"
          fill="{color}" opacity="0.85">
      <animate attributeName="width"
               from="0" to="{bar_w}"
               dur="0.8s" fill="freeze"/>
    </rect>

    <!-- النسبة -->
    <text x="{width - 140}" y="30"
          font-family="Arial" font-size="12"
          font-weight="bold"
          fill="{self.colors.text_color}">
      {win_rate_str}
    </text>

    <!-- الثقة -->
    <text x="{width - 80}" y="30"
          font-family="Arial" font-size="10"
          fill="#888">
      {md.get('confidence', '')}
    </text>
  </g>
'''

        svg += '</svg>'
        return svg

    # ──────────────────────────────────────
    # رسم حجر واحد كبير
    # ──────────────────────────────────────

    def render_single_tile_large(
        self,
        tile: DominoTile,
        label: str = "",
        width: int = 200,
        height: int = 140,
    ) -> str:
        """حجر واحد كبير (للتوصية)"""
        tw, th = 160, 80
        tx = (width - tw) // 2
        ty = 10

        old_w, old_h, old_r = self.tile_w, self.tile_h, self.pip_r
        self.tile_w, self.tile_h, self.pip_r = tw, th, 10
        self.half_w = tw // 2

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {width} {height}"
     width="{width}" height="{height}">
{self._svg_defs()}
'''
        svg += self.render_tile(
            tile, x=tx, y=ty,
            highlighted=True, selected=True
        )

        if label:
            svg += f'''
  <text x="{width // 2}" y="{height - 15}"
        text-anchor="middle"
        font-family="Arial" font-size="13"
        font-weight="bold"
        fill="{self.colors.highlight_border}">
    {label}
  </text>
'''

        svg += '</svg>'

        self.tile_w, self.tile_h, self.pip_r = old_w, old_h, old_r
        self.half_w = old_w // 2

        return svg

    # ──────────────────────────────────────
    # أدوات مساعدة
    # ──────────────────────────────────────

    @staticmethod
    def _darken(hex_color: str, amount: float) -> str:
        """تغميق لون"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r = max(0, int(hex_color[0:2], 16) - int(255 * amount))
        g = max(0, int(hex_color[2:4], 16) - int(255 * amount))
        b = max(0, int(hex_color[4:6], 16) - int(255 * amount))
        return f"#{r:02x}{g:02x}{b:02x}"
