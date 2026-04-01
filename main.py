# main.py
"""
نقطة البداية الرئيسية للمساعد الذكي
"""
from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, Move
)
from ai_brain.mcts import MCTSEngine
from ai_brain.strategy import StrategyAnalyzer
from ai_brain.probability import ProbabilityEngine
from ui.manual_input import ManualInput
from config import GameConfig

import os


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    print("""
╔══════════════════════════════════════════════╗
║       🎲 المساعد الذكي للدومينو 🎲          ║
║          Domino Genius Assistant              ║
╚══════════════════════════════════════════════╝
    """)


def main():
    config = GameConfig()
    
    print_header()
    
    # تهيئة اللعبة
    state = GameState()
    state.initialize_players()
    
    # إدخال أحجارك
    print("أولاً: أدخل أحجارك (7 أحجار)")
    
    # اختيار طريقة الإدخال
    print("\nكيف تريد إدخال أحجارك؟")
    print("[1] يدوياً")
    print("[2] من صورة (كاميرا)")
    print("[3] من ملف صورة")
    
    choice = input(">>> ").strip()
    
    if choice == '1':
        my_tiles = ManualInput.input_tiles(
            "أدخل أحجارك السبعة:"
        )
    elif choice in ('2', '3'):
        try:
            from vision.detector import DominoDetector
            detector = DominoDetector(method="opencv")
            
            if choice == '2':
                results = detector.detect_from_camera()
            else:
                import cv2
                path = input("مسار الصورة: ").strip()
                image = cv2.imread(path)
                results = detector.detect_from_image(image)
            
            my_tiles = ManualInput.review_detection(results)
        except ImportError:
            print("⚠️ OpenCV غير مثبت. الإدخال اليدوي:")
            my_tiles = ManualInput.input_tiles(
                "أدخل أحجارك:"
            )
    else:
        my_tiles = ManualInput.input_tiles(
            "أدخل أحجارك:"
        )
    
    state.set_my_hand(my_tiles)
    
    # حلقة اللعبة الرئيسية
    mcts_engine = MCTSEngine(config)
    
    print("\n✅ اللعبة جاهزة! لنبدأ.")
    
    while not state.is_game_over:
        clear_screen()
        print_header()
        print(state.display_status())
        
        current = state.current_turn
        
        if current == PlayerPosition.SOUTH:
            # === دورك ===
            print("\n🎯 دورك!")
            
            valid_moves = state.get_valid_moves(
                PlayerPosition.SOUTH
            )
            
            if len(valid_moves) == 1 and valid_moves[0].is_pass:
                print("😔 ما عندك حركة - دق!")
                state.apply_move(valid_moves[0])
                input("\nاضغط Enter للمتابعة...")
                continue
            
            # طلب التحليل الذكي
            print("\n⏳ جاري التحليل...")
            
            analyzer = StrategyAnalyzer(state)
            recommendation = analyzer.get_full_recommendation()
            print(recommendation)
            
            # عرض الخيارات
            print("\nخياراتك:")
            for i, move in enumerate(valid_moves):
                print(f"  [{i+1}] {move}")
            
            print(
                f"\n  [0] استخدام التوصية "
                f"(الحركة الأولى)"
            )
            
            while True:
                try:
                    choice_idx = int(
                        input("\naختر حركة: ").strip()
                    )
                    if choice_idx == 0:
                        best_move, _ = (
                            mcts_engine.find_best_move(state)
                        )
                        state.apply_move(best_move)
                        break
                    elif 1 <= choice_idx <= len(valid_moves):
                        state.apply_move(
                            valid_moves[choice_idx - 1]
                        )
                        break
                    else:
                        print("رقم غير صحيح")
                except ValueError:
                    print("أدخل رقماً")
        
        else:
            # === دور الخصم/الشريك ===
            move = ManualInput.input_opponent_move(state)
            
            if not move.is_pass and move.tile:
                # لو لعب حجر، نحتاج نقلل عدد أحجاره
                state.players[current].tiles_count -= 1
                state.players[current].played_tiles.append(
                    move.tile
                )
            
            state.apply_move(move)
        
        input("\nاضغط Enter للمتابعة...")
    
    # نهاية اللعبة
    clear_screen()
    print_header()
    print("\n" + "🏆" * 20)
    print("انتهت اللعبة!")
    
    if state.winner:
        if state.winner in (
            PlayerPosition.SOUTH, 
            PlayerPosition.NORTH
        ):
            print("🎉 مبروك! فريقك فاز!")
        else:
            print("😞 خسرت هذه الجولة")
    else:
        print("🤝 تعادل")
    
    print(state.display_status())


if __name__ == "__main__":
    main()
