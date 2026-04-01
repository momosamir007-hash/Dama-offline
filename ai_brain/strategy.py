# ai_brain/strategy.py
"""
استراتيجيات متقدمة تعمل فوق MCTS
"""
from typing import List, Dict, Tuple, Optional
from game_engine.game_state import (
    GameState, Move, PlayerPosition
)
from game_engine.domino_board import DominoTile, Direction
from ai_brain.probability import ProbabilityEngine


class StrategyAnalyzer:
    """
    محلل استراتيجي يضيف طبقة ذكاء فوق MCTS
    يقدم نصائح وتفسيرات للحركة المقترحة
    """
    
    def __init__(self, game_state: GameState):
        self.state = game_state
        self.prob_engine = ProbabilityEngine(game_state)
    
    def analyze_move(self, move: Move) -> Dict:
        """تحليل شامل لحركة معينة"""
        if move.is_pass:
            return {'type': 'pass', 'reason': 'لا يوجد حجر مناسب'}
        
        analysis = {
            'move': str(move),
            'reasons': [],
            'risks': [],
            'score': 0.0
        }
        
        # 1. تحليل التحكم بالأرقام
        control = self._analyze_number_control(move)
        analysis['reasons'].extend(control['benefits'])
        analysis['risks'].extend(control['risks'])
        analysis['score'] += control['score']
        
        # 2. تحليل إمكانية القفل
        blocking = self._analyze_blocking(move)
        analysis['reasons'].extend(blocking['benefits'])
        analysis['score'] += blocking['score']
        
        # 3. تحليل التخفيف (تقليل مجموع النقاط)
        weight = self._analyze_weight_reduction(move)
        analysis['reasons'].extend(weight['benefits'])
        analysis['score'] += weight['score']
        
        # 4. تحليل مساعدة الشريك
        partner = self._analyze_partner_help(move)
        analysis['reasons'].extend(partner['benefits'])
        analysis['score'] += partner['score']
        
        return analysis
    
    def _analyze_number_control(self, move: Move) -> Dict:
        """
        هل هذه الحركة تعطيني تحكم بالأرقام على الطاولة؟
        
        مثال: لو عندي 3 أحجار فيها رقم 5
        ولعبت حجر يخلي الطرفين 5 و 5
        = أنا متحكم ولا أحد يقدر يلعب 5 غيري
        """
        result = {
            'benefits': [], 
            'risks': [], 
            'score': 0.0
        }
        
        # كم حجر عندي من نفس الأرقام الموجودة على الأطراف
        sim_state = self.state.clone()
        sim_state.apply_move(move)
        
        if sim_state.board.is_empty:
            return result
        
        for end_value in sim_state.board.open_ends:
            my_tiles_with_value = sum(
                1 for t in self.state.my_hand 
                if t != move.tile and t.has_value(end_value)
            )
            
            remaining = self.state.get_remaining_count_per_value()
            total_remaining = remaining.get(end_value, 0)
            
            if my_tiles_with_value > 0 and total_remaining <= 3:
                result['benefits'].append(
                    f"💪 تحكم بالرقم {end_value}: "
                    f"عندك {my_tiles_with_value} أحجار "
                    f"من أصل {total_remaining} متبقية"
                )
                result['score'] += 3.0
        
        return result
    
    def _analyze_blocking(self, move: Move) -> Dict:
        """هل هذه الحركة تقفل على الخصم؟"""
        result = {'benefits': [], 'score': 0.0}
        
        sim_state = self.state.clone()
        sim_state.apply_move(move)
        
        for pos in [PlayerPosition.WEST, PlayerPosition.EAST]:
            player = sim_state.players[pos]
            # لو الخصم دق على أحد الأطراف الناتجة
            for end_value in sim_state.board.open_ends:
                if end_value in player.passed_values:
                    result['benefits'].append(
                        f"🚫 تقفل على {pos.name}: "
                        f"ما عنده رقم {end_value}"
                    )
                    result['score'] += 2.5
        
        return result
    
    def _analyze_weight_reduction(self, move: Move) -> Dict:
        """هل نتخلص من حجر ثقيل؟"""
        result = {'benefits': [], 'score': 0.0}
        
        if move.tile.total >= 9:
            result['benefits'].append(
                f"⚖️ تخلص من حجر ثقيل: "
                f"{move.tile} = {move.tile.total} نقطة"
            )
            result['score'] += 1.5
        
        if move.tile.is_double and move.tile.total >= 8:
            result['benefits'].append(
                f"🎯 تخلص من دبل ثقيل: {move.tile}"
            )
            result['score'] += 2.0
        
        return result
    
    def _analyze_partner_help(self, move: Move) -> Dict:
        """هل هذه الحركة تساعد الشريك؟"""
        result = {'benefits': [], 'score': 0.0}
        
        partner = self.state.players[PlayerPosition.NORTH]
        
        # لو الشريك لعب أحجار كثيرة من رقم معين
        # يعني يحب هالرقم - نحاول نفتح له
        partner_preferred = {}
        for tile in partner.played_tiles:
            for val in tile.pip_values:
                partner_preferred[val] = (
                    partner_preferred.get(val, 0) + 1
                )
        
        sim_state = self.state.clone()
        sim_state.apply_move(move)
        
        for end_value in sim_state.board.open_ends:
            if partner_preferred.get(end_value, 0) >= 2:
                result['benefits'].append(
                    f"🤝 تفتح للشريك رقم {end_value}: "
                    f"لعب منه {partner_preferred[end_value]} مرات"
                )
                result['score'] += 2.0
        
        return result
    
    def get_full_recommendation(self) -> str:
        """
        تقرير كامل بالتوصية
        """
        from ai_brain.mcts import MCTSEngine
        
        engine = MCTSEngine()
        best_move, analysis = engine.find_best_move(self.state)
        
        move_analysis = self.analyze_move(best_move)
        
        lines = [
            "\n" + "🧠" * 20,
            "تحليل المساعد الذكي",
            "🧠" * 20,
            "",
            f"⭐ الحركة المقترحة: {best_move}",
            f"📊 محاكاات: {analysis['total_simulations']}",
            f"⏱️ وقت التحليل: {analysis['time_elapsed']}",
            "",
            "الأسباب:",
        ]
        
        for reason in move_analysis.get('reasons', []):
            lines.append(f"  {reason}")
        
        if move_analysis.get('risks'):
            lines.append("\nالمخاطر:")
            for risk in move_analysis['risks']:
                lines.append(f"  ⚠️ {risk}")
        
        lines.append("\nتحليل كل الخيارات:")
        for ma in analysis['moves_analysis'][:5]:
            lines.append(
                f"  {ma['move']}: "
                f"فوز {ma['win_rate']} "
                f"{ma['confidence']} "
                f"({ma['visits']} محاكاة)"
            )
        
        return "\n".join(lines)
