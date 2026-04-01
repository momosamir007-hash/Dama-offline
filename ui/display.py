# ui/display.py
"""
نظام العرض المرئي للعبة الدومينو
يعرض الطاولة واليد والتحليلات بشكل جميل في الطرفية
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import os
import sys

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo, Move
)


# ──────────────────────────────────────────────
# الألوان والرموز
# ──────────────────────────────────────────────

class Colors:
    """ألوان ANSI للطرفية"""
    # أساسية
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    
    # نص
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # خلفية
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # ألوان مشرقة
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_CYAN = "\033[96m"
    
    @classmethod
    def disable(cls):
        """تعطيل الألوان (لأنظمة لا تدعمها)"""
        for attr in dir(cls):
            if (
                not attr.startswith('_') and 
                attr != 'disable' and
                attr != 'enable' and
                isinstance(getattr(cls, attr), str)
            ):
                setattr(cls, attr, "")
    
    @classmethod
    def is_supported(cls) -> bool:
        """هل النظام يدعم الألوان؟"""
        if os.name == 'nt':
            # Windows 10+ يدعمها
            return True
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


# ──────────────────────────────────────────────
# رسم حجر الدومينو
# ──────────────────────────────────────────────

class TileRenderer:
    """رسم حجر دومينو في الطرفية"""
    
    # أنماط النقاط لكل رقم (3×3 grid)
    PIP_PATTERNS = {
        0: [
            "     ",
            "     ",
            "     ",
        ],
        1: [
            "     ",
            "  ●  ",
            "     ",
        ],
        2: [
            "    ●",
            "     ",
            "●    ",
        ],
        3: [
            "    ●",
            "  ●  ",
            "●    ",
        ],
        4: [
            "●   ●",
            "     ",
            "●   ●",
        ],
        5: [
            "●   ●",
            "  ●  ",
            "●   ●",
        ],
        6: [
            "●   ●",
            "●   ●",
            "●   ●",
        ],
    }
    
    @classmethod
    def render_tile(
        cls,
        tile: DominoTile,
        highlight: bool = False,
        color: str = ""
    ) -> List[str]:
        """
        رسم حجر واحد
        
        ┌─────┬─────┐
        │●   ●│    ●│
        │  ●  │  ●  │
        │●   ●│●    │
        └─────┴─────┘
        """
        c = color or Colors.WHITE
        r = Colors.RESET
        
        if highlight:
            c = Colors.BRIGHT_GREEN + Colors.BOLD
        
        left_pattern = cls.PIP_PATTERNS.get(
            tile.high, cls.PIP_PATTERNS[0]
        )
        right_pattern = cls.PIP_PATTERNS.get(
            tile.low, cls.PIP_PATTERNS[0]
        )
        
        lines = [
            f"{c}┌─────┬─────┐{r}",
            f"{c}│{left_pattern[0]}│{right_pattern[0]}│{r}",
            f"{c}│{left_pattern[1]}│{right_pattern[1]}│{r}",
            f"{c}│{left_pattern[2]}│{right_pattern[2]}│{r}",
            f"{c}└─────┴─────┘{r}",
        ]
        
        return lines
    
    @classmethod
    def render_tile_compact(
        cls,
        tile: DominoTile,
        highlight: bool = False
    ) -> str:
        """رسم مختصر: [5|3]"""
        if highlight:
            return (
                f"{Colors.BRIGHT_GREEN}{Colors.BOLD}"
                f"[{tile.high}|{tile.low}]"
                f"{Colors.RESET}"
            )
        return f"[{tile.high}|{tile.low}]"
    
    @classmethod
    def render_hand(
        cls,
        tiles: List[DominoTile],
        highlight_indices: List[int] = None
    ) -> str:
        """
        رسم يد كاملة بجانب بعض
        """
        if not tiles:
            return "  [ اليد فارغة ]"
        
        highlight_indices = highlight_indices or []
        
        # رسم كل حجر
        all_renders = []
        for i, tile in enumerate(tiles):
            is_highlighted = i in highlight_indices
            rendered = cls.render_tile(
                tile, highlight=is_highlighted
            )
            all_renders.append(rendered)
        
        # دمج الأحجار بجانب بعض
        result_lines = []
        num_lines = len(all_renders[0])
        
        for line_idx in range(num_lines):
            parts = []
            for tile_render in all_renders:
                parts.append(tile_render[line_idx])
            result_lines.append(" ".join(parts))
        
        # إضافة أرقام تحت كل حجر
        numbers_line = "  "
        for i in range(len(tiles)):
            num_str = f"  ({i+1})    "
            if i in highlight_indices:
                num_str = (
                    f"{Colors.BRIGHT_GREEN}"
                    f"  ({i+1})★   "
                    f"{Colors.RESET}"
                )
            numbers_line += num_str
        
        result_lines.append(numbers_line)
        
        return "\n".join(result_lines)


# ──────────────────────────────────────────────
# العرض الرئيسي
# ──────────────────────────────────────────────

class GameDisplay:
    """
    العرض الرئيسي للعبة
    يرسم الطاولة بشكل بصري جميل
    """
    
    def __init__(self, use_colors: bool = True):
        self.renderer = TileRenderer()
        
        if not use_colors or not Colors.is_supported():
            Colors.disable()
    
    def clear(self):
        """مسح الشاشة"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_header(self):
        """عرض رأس التطبيق"""
        header = f"""
{Colors.BRIGHT_CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════╗
║          🎲  المساعد الذكي للدومينو  🎲          ║
║             Domino Genius Assistant               ║
╚══════════════════════════════════════════════════╝
{Colors.RESET}"""
        print(header)
    
    def show_table_layout(self, state: GameState):
        """
        عرض ترتيب الطاولة من منظور اللاعب
        
                    [NORTH - شريكك]
                    أحجار: X
                    
        [WEST]                          [EAST]
        أحجار: X                        أحجار: X
                    
                    ══ الطاولة ══
                [طرف] ─── [أحجار] ─── [طرف]
                    
                    [SOUTH - أنت]
                    يدك: [أحجارك]
        """
        c = Colors
        
        # اللاعب الشمالي (الشريك)
        north = state.players[PlayerPosition.NORTH]
        north_info = self._player_info_box(
            "شريكك (الشمالي)", 
            north,
            c.BRIGHT_BLUE
        )
        
        # اللاعب الغربي
        west = state.players[PlayerPosition.WEST]
        west_info = self._player_info_compact(
            "الخصم الأيمن", west, c.RED
        )
        
        # اللاعب الشرقي
        east = state.players[PlayerPosition.EAST]
        east_info = self._player_info_compact(
            "الخصم الأيسر", east, c.RED
        )
        
        # الطاولة
        board_display = self._render_board(state.board)
        
        # الطاولة الكاملة
        print(f"""
{self._center_text(north_info, 60)}

{west_info:<30}{'':>5}{east_info:>30}

{c.YELLOW}{'═' * 60}{c.RESET}
{board_display}
{c.YELLOW}{'═' * 60}{c.RESET}
""")
    
    def show_my_hand(
        self, 
        state: GameState,
        valid_move_indices: List[int] = None
    ):
        """عرض يدي"""
        c = Colors
        
        print(
            f"\n{c.BRIGHT_GREEN}{c.BOLD}"
            f"🃏 أحجارك ({len(state.my_hand)} أحجار):"
            f"{c.RESET}"
        )
        
        hand_display = self.renderer.render_hand(
            state.my_hand,
            highlight_indices=valid_move_indices or []
        )
        print(hand_display)
        
        # مجموع النقاط
        total = sum(t.total for t in state.my_hand)
        print(
            f"\n  {c.DIM}مجموع النقاط: {total}{c.RESET}"
        )
    
    def show_valid_moves(
        self, 
        moves: List[Move],
        analysis: Dict = None
    ):
        """عرض الحركات المتاحة"""
        c = Colors
        
        print(
            f"\n{c.BOLD}📋 الحركات المتاحة:{c.RESET}"
        )
        
        for i, move in enumerate(moves):
            if move.is_pass:
                print(
                    f"  {c.RED}[{i+1}] دق (Pass) 🚫{c.RESET}"
                )
            else:
                dir_arrow = (
                    "⬅️" if move.direction == Direction.LEFT 
                    else "➡️"
                )
                dir_name = (
                    "يسار" 
                    if move.direction == Direction.LEFT 
                    else "يمين"
                )
                
                # لو فيه تحليل: نضيف نسبة الفوز
                extra = ""
                if analysis and i < len(analysis.get(
                    'moves_analysis', []
                )):
                    ma = analysis['moves_analysis'][i]
                    extra = (
                        f" {c.DIM}| فوز: {ma['win_rate']} "
                        f"{ma['confidence']}{c.RESET}"
                    )
                
                print(
                    f"  {c.GREEN}[{i+1}]{c.RESET} "
                    f"{move.tile} {dir_arrow} {dir_name}"
                    f"{extra}"
                )
    
    def show_recommendation(
        self,
        best_move: Move,
        analysis: Dict,
        strategy_info: Dict = None
    ):
        """عرض توصية الذكاء الاصطناعي"""
        c = Colors
        
        print(f"""
{c.BG_BLUE}{c.WHITE}{c.BOLD}
╔══════════════════════════════════════════╗
║          🧠 توصية المساعد الذكي          ║
╚══════════════════════════════════════════╝
{c.RESET}""")
        
        # الحركة المقترحة
        if best_move.is_pass:
            print(f"  {c.RED}💡 التوصية: دق (Pass){c.RESET}")
        else:
            dir_name = (
                "يسار" 
                if best_move.direction == Direction.LEFT 
                else "يمين"
            )
            print(
                f"  {c.BRIGHT_GREEN}{c.BOLD}"
                f"💡 التوصية: العب {best_move.tile} "
                f"على ال{dir_name}"
                f"{c.RESET}"
            )
        
        # إحصائيات التحليل
        print(
            f"\n  {c.CYAN}📊 محاكاات: "
            f"{analysis['total_simulations']}"
            f" | ⏱️ {analysis['time_elapsed']}"
            f"{c.RESET}"
        )
        
        # الأسباب
        if strategy_info and strategy_info.get('reasons'):
            print(f"\n  {c.BOLD}الأسباب:{c.RESET}")
            for reason in strategy_info['reasons']:
                print(f"    {reason}")
        
        # المخاطر
        if strategy_info and strategy_info.get('risks'):
            print(f"\n  {c.BOLD}المخاطر:{c.RESET}")
            for risk in strategy_info['risks']:
                print(f"    ⚠️  {risk}")
        
        # ترتيب كل الحركات
        print(f"\n  {c.BOLD}ترتيب الخيارات:{c.RESET}")
        for i, ma in enumerate(
            analysis.get('moves_analysis', [])[:5]
        ):
            rank_icon = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            icon = rank_icon[i] if i < 5 else f" {i+1}."
            
            print(
                f"    {icon} {ma['move']} "
                f"→ فوز {ma['win_rate']} "
                f"{ma['confidence']}"
            )
    
    def show_move_result(
        self, 
        move: Move, 
        state: GameState
    ):
        """عرض نتيجة الحركة"""
        c = Colors
        
        name_map = {
            PlayerPosition.SOUTH: (
                f"{c.GREEN}أنت{c.RESET}"
            ),
            PlayerPosition.WEST: (
                f"{c.RED}الخصم الأيمن{c.RESET}"
            ),
            PlayerPosition.NORTH: (
                f"{c.BLUE}شريكك{c.RESET}"
            ),
            PlayerPosition.EAST: (
                f"{c.RED}الخصم الأيسر{c.RESET}"
            ),
        }
        
        player_name = name_map.get(
            move.player, str(move.player)
        )
        
        if move.is_pass:
            print(
                f"\n  {c.YELLOW}🔸 {player_name} "
                f"دق (Pass){c.RESET}"
            )
        else:
            dir_name = (
                "يسار" 
                if move.direction == Direction.LEFT 
                else "يمين"
            )
            print(
                f"\n  {c.BOLD}🔹 {player_name} "
                f"لعب {move.tile} "
                f"على ال{dir_name}{c.RESET}"
            )
    
    def show_game_over(self, state: GameState):
        """عرض نهاية اللعبة"""
        c = Colors
        
        is_win = state.winner in (
            PlayerPosition.SOUTH, 
            PlayerPosition.NORTH
        )
        
        if is_win:
            print(f"""
{c.BG_GREEN}{c.WHITE}{c.BOLD}
╔══════════════════════════════════════════╗
║                                          ║
║          🏆  مبروك! فريقك فاز!  🏆       ║
║                                          ║
╚══════════════════════════════════════════╝
{c.RESET}""")
        elif state.winner:
            print(f"""
{c.BG_RED}{c.WHITE}{c.BOLD}
╔══════════════════════════════════════════╗
║                                          ║
║        😔  خسرت هذه الجولة  😔           ║
║                                          ║
╚══════════════════════════════════════════╝
{c.RESET}""")
        else:
            print(f"""
{c.BG_YELLOW}{c.BLACK}{c.BOLD}
╔══════════════════════════════════════════╗
║                                          ║
║             🤝  تعادل  🤝                ║
║                                          ║
╚══════════════════════════════════════════╝
{c.RESET}""")
        
        # تفاصيل النقاط
        self.show_score_summary(state)
    
    def show_score_summary(self, state: GameState):
        """ملخص النقاط"""
        c = Colors
        
        print(f"\n{c.BOLD}📊 ملخص النقاط:{c.RESET}")
        
        for pos in PlayerPosition:
            player = state.players[pos]
            total = player.hand_total
            tiles_left = len(player.hand)
            
            name_map = {
                PlayerPosition.SOUTH: "أنت        ",
                PlayerPosition.WEST:  "الخصم الأيمن",
                PlayerPosition.NORTH: "شريكك      ",
                PlayerPosition.EAST:  "الخصم الأيسر",
            }
            
            name = name_map.get(pos, str(pos))
            
            color = c.GREEN if pos in (
                PlayerPosition.SOUTH, 
                PlayerPosition.NORTH
            ) else c.RED
            
            bar = "█" * min(total, 40)
            
            print(
                f"  {color}{name}: "
                f"{total:3d} نقطة "
                f"({tiles_left} أحجار) "
                f"{c.DIM}{bar}{c.RESET}"
            )
    
    def show_probability_table(
        self, 
        probabilities: Dict
    ):
        """عرض جدول الاحتمالات"""
        c = Colors
        
        print(f"""
{c.BOLD}{c.CYAN}
╔══════════════════════════════════════════╗
║       📊 احتمالات أحجار الخصوم          ║
╚══════════════════════════════════════════╝
{c.RESET}""")
        
        name_map = {
            PlayerPosition.WEST: "الخصم الأيمن",
            PlayerPosition.NORTH: "الشريك",
            PlayerPosition.EAST: "الخصم الأيسر",
        }
        
        for pos in [
            PlayerPosition.WEST,
            PlayerPosition.NORTH, 
            PlayerPosition.EAST
        ]:
            if pos not in probabilities:
                continue
            
            print(f"\n  {c.BOLD}{name_map[pos]}:{c.RESET}")
            
            sorted_tiles = sorted(
                probabilities[pos].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for tile, prob in sorted_tiles[:8]:
                if prob < 0.01:
                    continue
                
                bar_len = int(prob * 25)
                bar = "▓" * bar_len + "░" * (25 - bar_len)
                
                prob_color = (
                    c.RED if prob > 0.6
                    else c.YELLOW if prob > 0.3
                    else c.DIM
                )
                
                print(
                    f"    {tile} {prob_color}"
                    f"{bar} {prob:.0%}{c.RESET}"
                )
    
    def show_move_history(
        self, 
        moves: List[Move],
        last_n: int = 10
    ):
        """عرض آخر الحركات"""
        c = Colors
        
        print(
            f"\n{c.BOLD}📜 آخر الحركات:{c.RESET}"
        )
        
        recent = moves[-last_n:] if moves else []
        
        for i, move in enumerate(recent):
            move_num = len(moves) - len(recent) + i + 1
            
            icon_map = {
                PlayerPosition.SOUTH: "🟢",
                PlayerPosition.WEST: "🔴",
                PlayerPosition.NORTH: "🔵",
                PlayerPosition.EAST: "🔴",
            }
            
            icon = icon_map.get(move.player, "⚪")
            
            if move.is_pass:
                print(
                    f"  {c.DIM}{move_num:2d}. "
                    f"{icon} {move.player.name}: "
                    f"دق{c.RESET}"
                )
            else:
                print(
                    f"  {move_num:2d}. {icon} "
                    f"{move.player.name}: "
                    f"{move.tile} → "
                    f"{move.direction.value}"
                )
    
    # ──────────────────────────────────────────
    # أدوات مساعدة
    # ──────────────────────────────────────────
    
    def _player_info_box(
        self, 
        name: str,
        player: PlayerInfo,
        color: str
    ) -> str:
        """معلومات لاعب في صندوق"""
        c = Colors
        passed = (
            ", ".join(str(v) for v in player.passed_values)
            if player.passed_values else "—"
        )
        
        return (
            f"{color}{c.BOLD}{name}{c.RESET}\n"
            f"  أحجار: {player.tiles_count} | "
            f"دق على: {passed}"
        )
    
    def _player_info_compact(
        self,
        name: str,
        player: PlayerInfo,
        color: str
    ) -> str:
        """معلومات لاعب مختصرة"""
        c = Colors
        tiles_visual = "🀫 " * player.tiles_count
        
        return (
            f"{color}{c.BOLD}{name}{c.RESET}\n"
            f"  {tiles_visual}\n"
            f"  {c.DIM}({player.tiles_count} أحجار){c.RESET}"
        )
    
    def _render_board(self, board: Board) -> str:
        """رسم الطاولة"""
        c = Colors
        
        if board.is_empty:
            return (
                f"  {c.DIM}[ الطاولة فارغة - "
                f"في انتظار أول حجر ]{c.RESET}"
            )
        
        # عرض سلسلة الأحجار
        chain_parts = []
        for tile, direction in board.tiles_played:
            chain_parts.append(
                self.renderer.render_tile_compact(tile)
            )
        
        chain = " ── ".join(chain_parts)
        
        # تقسيم لأسطر لو طويلة
        max_width = 55
        lines = []
        current_line = ""
        
        for part in chain_parts:
            test = (
                current_line + " ── " + part 
                if current_line else part
            )
            if len(test) > max_width and current_line:
                lines.append(current_line)
                current_line = "    " + part  # مسافة بادئة
            else:
                current_line = test
        
        if current_line:
            lines.append(current_line)
        
        result = "\n".join(
            f"  {line}" for line in lines
        )
        
        # الأطراف
        result += (
            f"\n\n  {c.BOLD}الأطراف: "
            f"{c.BRIGHT_YELLOW}[{board.left_end}]"
            f"{c.RESET} ←── الطاولة ──→ "
            f"{c.BRIGHT_YELLOW}[{board.right_end}]"
            f"{c.RESET}"
        )
        
        return result
    
    def _center_text(self, text: str, width: int) -> str:
        """توسيط النص"""
        lines = text.split('\n')
        centered = []
        for line in lines:
            # حساب الطول بدون ألوان ANSI
            clean_len = len(
                line.encode('ascii', 'ignore').decode()
            )
            padding = max(0, (width - clean_len) // 2)
            centered.append(" " * padding + line)
        return "\n".join(centered)
    
    def show_loading(self, message: str = "جاري التحليل"):
        """عرض رسالة انتظار"""
        c = Colors
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        print(
            f"  {c.CYAN}{frames[0]} "
            f"{message}...{c.RESET}",
            end="\r"
        )
    
    def show_separator(self, char: str = "─", width: int = 50):
        """خط فاصل"""
        print(f"  {Colors.DIM}{char * width}{Colors.RESET}")
    
    def prompt(self, message: str) -> str:
        """طلب إدخال من المستخدم"""
        c = Colors
        return input(
            f"\n  {c.BRIGHT_CYAN}❯ {message}: {c.RESET}"
        ).strip()
