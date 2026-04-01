"""
محرك رسم SVG
بدون TileTheme - لتجنب أخطاء الاستيراد
"""
import streamlit.components.v1 as components
from typing import List, Optional
from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import GameState, PlayerPosition


PIP_POSITIONS = {
    0: [],
    1: [(0.5, 0.5)],
    2: [(0.25, 0.75), (0.75, 0.25)],
    3: [(0.25, 0.75), (0.5, 0.5), (0.75, 0.25)],
    4: [(0.25, 0.25), (0.25, 0.75),
        (0.75, 0.25), (0.75, 0.75)],
    5: [(0.25, 0.25), (0.25, 0.75), (0.5, 0.5),
        (0.75, 0.25), (0.75, 0.75)],
    6: [(0.25, 0.25), (0.25, 0.5), (0.25, 0.75),
        (0.75, 0.25), (0.75, 0.5), (0.75, 0.75)],
}


class DominoSVG:
    def __init__(self, tw=120, th=60, pr=7, sp=12):
        self.tw = tw
        self.th = th
        self.pr = pr
        self.sp = sp
        self.hw = tw // 2

    # ═══════════════════════════════
    # عرض SVG
    # ═══════════════════════════════

    @staticmethod
    def display(svg_code: str, height: int = 200):
        html = f"""
        <div style="
            display:flex;
            justify-content:center;
            align-items:center;
            width:100%;
            overflow-x:auto;
            padding:10px 0;
            background:transparent;
        ">
            {svg_code}
        </div>
        """
        components.html(html, height=height, scrolling=True)

    # ═══════════════════════════════
    # حجر واحد
    # ═══════════════════════════════

    def _pips(self, count, ox, oy, aw, ah, dbl=False):
        pts = PIP_POSITIONS.get(count, [])
        clr = "#CC0000" if dbl else "#1a1a1a"
        pad = 10
        s = ""
        for px, py in pts:
            cx = ox + pad + px * (aw - 2 * pad)
            cy = oy + pad + py * (ah - 2 * pad)
            s += (
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" '
                f'r="{self.pr}" fill="{clr}"/>\n'
            )
        return s

    def tile_svg(self, tile, x=0, y=0, hl=False, label=""):
        fill = "#D5F5E3" if hl else "#FFFFFF"
        stroke = "#27AE60" if hl else "#2C3E50"
        sw = 3 if hl else 2

        s = f'<g transform="translate({x},{y})">\n'
        s += (
            f'<rect x="2" y="2" width="{self.tw}" '
            f'height="{self.th}" rx="8" '
            f'fill="rgba(0,0,0,0.15)"/>\n'
        )
        s += (
            f'<rect x="0" y="0" width="{self.tw}" '
            f'height="{self.th}" rx="8" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>\n'
        )
        s += (
            f'<line x1="{self.hw}" y1="5" '
            f'x2="{self.hw}" y2="{self.th-5}" '
            f'stroke="#95A5A6" stroke-width="2" '
            f'stroke-dasharray="3,3"/>\n'
        )
        s += self._pips(
            tile.high, 0, 0, self.hw, self.th, tile.is_double
        )
        s += self._pips(
            tile.low, self.hw, 0, self.hw, self.th, tile.is_double
        )
        if label:
            s += (
                f'<text x="{self.tw//2}" y="{self.th+18}" '
                f'text-anchor="middle" font-family="Arial" '
                f'font-size="13" fill="#ECF0F1" '
                f'font-weight="bold">{label}</text>\n'
            )
        s += '</g>\n'
        return s

    # ═══════════════════════════════
    # يد اللاعب
    # ═══════════════════════════════

    def hand_svg(self, tiles, highlighted=None, title="يدك"):
        highlighted = highlighted or []
        n = len(tiles)
        if n == 0:
            return (
                '<svg width="400" height="80" '
                'xmlns="http://www.w3.org/2000/svg">'
                '<rect x="5" y="5" width="390" height="70" '
                'rx="12" fill="#1a1a2e" stroke="#4CAF50" '
                'stroke-dasharray="8,4" stroke-width="2"/>'
                '<text x="200" y="48" text-anchor="middle" '
                'font-family="Arial" font-size="16" '
                'fill="#4CAF50">'
                '✨ اليد فارغة - دومينو!</text></svg>'
            )

        total_w = n * (self.tw + self.sp) + 40
        total_h = self.th + 60

        s = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {total_w} {total_h}" '
            f'width="{total_w}" height="{total_h}">\n'
        )
        s += (
            f'<text x="{total_w//2}" y="16" '
            f'text-anchor="middle" font-family="Arial" '
            f'font-size="14" font-weight="bold" '
            f'fill="#ECF0F1">'
            f'🃏 {title} ({n} أحجار)</text>\n'
        )

        for i, tile in enumerate(tiles):
            tx = 20 + i * (self.tw + self.sp)
            s += self.tile_svg(
                tile, tx, 24,
                hl=(i in highlighted),
                label=f"({i+1})",
            )

        pts = sum(t.total for t in tiles)
        s += (
            f'<text x="{total_w//2}" y="{total_h-3}" '
            f'text-anchor="middle" font-family="Arial" '
            f'font-size="12" fill="#BDC3C7">'
            f'مجموع: {pts}</text>\n'
        )
        s += '</svg>'
        return s

    def display_hand(self, tiles, highlighted=None, title="يدك"):
        svg = self.hand_svg(tiles, highlighted, title)
        self.display(svg, height=self.th + 75)

    # ═══════════════════════════════
    # الطاولة
    # ═══════════════════════════════

    def board_svg(self, board, width=850, height=200):
        if board.is_empty:
            return (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 {width} {height}" '
                f'width="{width}" height="{height}">'
                f'<rect x="0" y="0" width="{width}" '
                f'height="{height}" rx="14" fill="#1B5E20"/>'
                f'<rect x="3" y="3" width="{width-6}" '
                f'height="{height-6}" rx="12" fill="none" '
                f'stroke="#4CAF50" stroke-width="2" '
                f'stroke-dasharray="10,5"/>'
                f'<text x="{width//2}" y="{height//2-8}" '
                f'text-anchor="middle" font-family="Arial" '
                f'font-size="22" fill="rgba(255,255,255,0.8)">'
                f'🎲</text>'
                f'<text x="{width//2}" y="{height//2+20}" '
                f'text-anchor="middle" font-family="Arial" '
                f'font-size="16" fill="rgba(255,255,255,0.6)">'
                f'الطاولة فارغة</text></svg>'
            )

        played = board.all_played_tiles
        n = len(played)
        ttw = self.tw + self.sp
        chain_w = n * ttw + 100
        aw = max(width, chain_w)

        s = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {aw} {height}" '
            f'width="{aw}" height="{height}">\n'
        )
        s += (
            f'<rect x="0" y="0" width="{aw}" '
            f'height="{height}" rx="14" fill="#1B5E20"/>\n'
        )
        s += (
            f'<rect x="3" y="3" width="{aw-6}" '
            f'height="{height-6}" rx="12" fill="none" '
            f'stroke="#2E7D32" stroke-width="1.5"/>\n'
        )
        s += (
            f'<line x1="50" y1="{height//2}" '
            f'x2="{aw-50}" y2="{height//2}" '
            f'stroke="rgba(255,255,255,0.1)" '
            f'stroke-width="2" stroke-dasharray="10,5"/>\n'
        )

        sx = max(50, (aw - n * ttw) // 2)
        for i, tile in enumerate(played):
            s += self.tile_svg(
                tile,
                sx + i * ttw,
                (height - self.th) // 2,
            )

        # أطراف
        end_y = height // 2 - 18
        s += (
            f'<g transform="translate(8,{end_y})">'
            f'<rect width="36" height="36" rx="8" '
            f'fill="rgba(255,255,255,0.2)" '
            f'stroke="rgba(255,255,255,0.4)"/>'
            f'<text x="18" y="25" text-anchor="middle" '
            f'font-family="Arial" font-size="20" '
            f'font-weight="bold" fill="#FFF">'
            f'{board.left_end}</text></g>\n'
        )
        s += (
            f'<g transform="translate({aw-44},{end_y})">'
            f'<rect width="36" height="36" rx="8" '
            f'fill="rgba(255,255,255,0.2)" '
            f'stroke="rgba(255,255,255,0.4)"/>'
            f'<text x="18" y="25" text-anchor="middle" '
            f'font-family="Arial" font-size="20" '
            f'font-weight="bold" fill="#FFF">'
            f'{board.right_end}</text></g>\n'
        )

        s += (
            f'<text x="26" y="{height-8}" '
            f'text-anchor="middle" font-size="10" '
            f'fill="rgba(255,255,255,0.5)">⬅️ يسار</text>\n'
        )
        s += (
            f'<text x="{aw-26}" y="{height-8}" '
            f'text-anchor="middle" font-size="10" '
            f'fill="rgba(255,255,255,0.5)">يمين ➡️</text>\n'
        )
        s += '</svg>'
        return s

    def display_board(self, board, width=850, height=200):
        svg = self.board_svg(board, width, height)
        self.display(svg, height=height + 20)

    # ═══════════════════════════════
    # خريطة اللاعبين
    # ═══════════════════════════════

    def players_svg(self, state, width=700, height=420):
        cx, cy = width // 2, height // 2

        pos_xy = {
            PlayerPosition.SOUTH: (cx, height - 50),
            PlayerPosition.NORTH: (cx, 50),
            PlayerPosition.WEST: (80, cy),
            PlayerPosition.EAST: (width - 80, cy),
        }
        labels = {
            PlayerPosition.SOUTH: "أنت 🟢",
            PlayerPosition.NORTH: "شريكك 🔵",
            PlayerPosition.WEST: "خصم 🔴",
            PlayerPosition.EAST: "خصم 🟠",
        }
        clrs = {
            PlayerPosition.SOUTH: "#4CAF50",
            PlayerPosition.NORTH: "#2196F3",
            PlayerPosition.WEST: "#F44336",
            PlayerPosition.EAST: "#FF9800",
        }

        s = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">\n'
        )
        # طاولة
        s += (
            f'<ellipse cx="{cx}" cy="{cy}" '
            f'rx="{width//3}" ry="{height//4}" '
            f'fill="#1B5E20" stroke="#2E7D32" '
            f'stroke-width="2"/>\n'
        )
        s += (
            f'<text x="{cx}" y="{cy+5}" '
            f'text-anchor="middle" font-size="16" '
            f'fill="rgba(255,255,255,0.5)">'
            f'🎲 الطاولة</text>\n'
        )

        for pos in PlayerPosition:
            p = state.players[pos]
            px, py = pos_xy[pos]
            lbl = labels[pos]
            clr = clrs[pos]
            is_turn = (pos == state.current_turn)
            bw, bh = 130, 78
            bx = px - bw // 2
            by = py - bh // 2
            sw = "3" if is_turn else "1.5"

            # بطاقة
            s += (
                f'<rect x="{bx}" y="{by}" '
                f'width="{bw}" height="{bh}" rx="12" '
                f'fill="#1a1a2e" stroke="{clr}" '
                f'stroke-width="{sw}"/>\n'
            )
            # شريط علوي
            s += (
                f'<rect x="{bx}" y="{by}" '
                f'width="{bw}" height="24" rx="12" '
                f'fill="{clr}"/>\n'
            )
            s += (
                f'<rect x="{bx}" y="{by+14}" '
                f'width="{bw}" height="10" '
                f'fill="{clr}"/>\n'
            )
            # اسم
            s += (
                f'<text x="{px}" y="{by+17}" '
                f'text-anchor="middle" font-family="Arial" '
                f'font-size="12" font-weight="bold" '
                f'fill="white">{lbl}</text>\n'
            )
            # عدد
            tc = len(p.hand) if p.is_me else p.tiles_count
            tiles_icons = "🀫" * min(tc, 7)
            s += (
                f'<text x="{px}" y="{by+42}" '
                f'text-anchor="middle" font-family="Arial" '
                f'font-size="12" fill="#ECF0F1">'
                f'أحجار: {tc}</text>\n'
            )
            s += (
                f'<text x="{px}" y="{by+58}" '
                f'text-anchor="middle" '
                f'font-size="11">{tiles_icons}</text>\n'
            )
            # دق
            if p.passed_values:
                ps = ", ".join(
                    str(v) for v in sorted(p.passed_values)
                )
                s += (
                    f'<text x="{px}" y="{by+72}" '
                    f'text-anchor="middle" font-size="9" '
                    f'fill="#EF5350">🚫 دق: {ps}</text>\n'
                )
            # مؤشر دور
            if is_turn:
                s += (
                    f'<circle cx="{bx+bw-8}" cy="{by+8}" '
                    f'r="6" fill="#4CAF50">'
                    f'<animate attributeName="r" '
                    f'values="6;3;6" dur="1.5s" '
                    f'repeatCount="indefinite"/></circle>\n'
                )

        s += '</svg>'
        return s

    def display_players(self, state, width=700, height=420):
        svg = self.players_svg(state, width, height)
        self.display(svg, height=height + 10)

    # ═══════════════════════════════
    # تحليل الحركات
    # ═══════════════════════════════

    def analysis_svg(self, moves_data, width=600):
        if not moves_data:
            return ""
        n = min(len(moves_data), 6)
        bh = 40
        total_h = n * (bh + 8) + 55
        colors = [
            "#4CAF50", "#8BC34A", "#FFC107",
            "#FF9800", "#FF5722", "#9E9E9E",
        ]
        icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"]

        s = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {total_h}" '
            f'width="{width}" height="{total_h}">\n'
        )
        s += (
            f'<text x="{width//2}" y="22" '
            f'text-anchor="middle" font-family="Arial" '
            f'font-size="15" font-weight="bold" '
            f'fill="#ECF0F1">📊 تحليل الخيارات</text>\n'
        )

        for i, md in enumerate(moves_data[:n]):
            y = 38 + i * (bh + 8)
            try:
                wp = float(
                    md.get('win_rate', '0%').strip('%')
                ) / 100
            except (ValueError, AttributeError):
                wp = 0.0
            bw = max(10, int((width - 200) * wp))
            c = colors[i] if i < len(colors) else "#999"
            ic = icons[i] if i < len(icons) else f"{i+1}."

            s += f'<g transform="translate(15,{y})">\n'
            s += f'<text x="0" y="22" font-size="18">{ic}</text>\n'
            s += (
                f'<text x="32" y="14" font-family="Arial" '
                f'font-size="11" fill="#BDC3C7">'
                f'{md.get("move","?")}</text>\n'
            )
            s += (
                f'<rect x="32" y="20" '
                f'width="{width-200}" height="14" '
                f'rx="7" fill="#2C3E50"/>\n'
            )
            s += (
                f'<rect x="32" y="20" width="{bw}" '
                f'height="14" rx="7" fill="{c}" '
                f'opacity="0.9"/>\n'
            )
            s += (
                f'<text x="{width-155}" y="32" '
                f'font-family="Arial" font-size="14" '
                f'font-weight="bold" fill="#ECF0F1">'
                f'{md.get("win_rate","")}</text>\n'
            )
            s += (
                f'<text x="{width-85}" y="32" '
                f'font-family="Arial" font-size="10" '
                f'fill="#95A5A6">'
                f'{md.get("confidence","")}</text>\n'
            )
            s += '</g>\n'

        s += '</svg>'
        return s

    def display_analysis(self, moves_data, width=600):
        svg = self.analysis_svg(moves_data, width)
        if svg:
            n = min(len(moves_data), 6)
            self.display(svg, height=n * 50 + 65)

    # ═══════════════════════════════
    # حجر كبير
    # ═══════════════════════════════

    def big_tile_svg(self, tile, label="", width=220, height=140):
        tw, th = 160, 80
        tx = (width - tw) // 2
        old = (self.tw, self.th, self.pr, self.hw)
        self.tw, self.th, self.pr, self.hw = tw, th, 10, tw // 2

        s = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">\n'
        )
        s += self.tile_svg(tile, tx, 10, hl=True)
        if label:
            s += (
                f'<text x="{width//2}" y="{height-12}" '
                f'text-anchor="middle" font-family="Arial" '
                f'font-size="13" font-weight="bold" '
                f'fill="#4CAF50">{label}</text>\n'
            )
        s += '</svg>'

        self.tw, self.th, self.pr, self.hw = old
        return s

    def display_big_tile(self, tile, label=""):
        svg = self.big_tile_svg(tile, label)
        self.display(svg, height=150)
