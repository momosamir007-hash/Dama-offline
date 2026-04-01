# ui/manual_input.py
"""
واجهة الإدخال اليدوي والمراجعة
"""
from typing import List, Optional, Tuple
from game_engine.domino_board import DominoTile, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, Move
)
from vision.detector import DetectionResult


class ManualInput:
    """
    واجهة للإدخال اليدوي ومراجعة نتائج الرؤية
    """
    
    @staticmethod
    def input_tiles(prompt: str = "أدخل الأحجار") -> List[DominoTile]:
        """
        إدخال أحجار يدوياً
        
        الصيغة: 6-4 5-5 3-1 0-0
        """
        print(f"\n{prompt}")
        print("الصيغة: رقم-رقم مفصولة بمسافات")
        print("مثال: 6-4 5-5 3-1 0-0")
        print("اكتب 'done' للانتهاء")
        
        tiles = []
        
        while True:
            line = input(">>> ").strip()
            
            if line.lower() == 'done':
                break
            
            parts = line.split()
            for part in parts:
                try:
                    nums = part.split('-')
                    if len(nums) == 2:
                        a, b = int(nums[0]), int(nums[1])
                        if 0 <= a <= 6 and 0 <= b <= 6:
                            tiles.append(DominoTile(a, b))
                            print(f"  ✅ أُضيف: [{a}|{b}]")
                        else:
                            print(f"  ❌ رقم خارج النطاق: {part}")
                    else:
                        print(f"  ❌ صيغة خاطئة: {part}")
                except ValueError:
                    print(f"  ❌ إدخال غير صحيح: {part}")
        
        return tiles
    
    @staticmethod
    def review_detection(
        results: List[DetectionResult]
    ) -> List[DominoTile]:
        """
        مراجعة نتائج الاكتشاف التلقائي
        """
        print("\n" + "=" * 50)
        print("📋 مراجعة الأحجار المكتشفة")
        print("=" * 50)
        
        confirmed_tiles = []
        
        for i, result in enumerate(results):
            confidence_icon = (
                "🟢" if result.confidence >= 0.8
                else "🟡" if result.confidence >= 0.6
                else "🔴"
            )
            
            print(
                f"\n{i+1}. {confidence_icon} "
                f"{result.tile} "
                f"(ثقة: {result.confidence:.0%})"
            )
            
            response = input(
                "   [Enter] لتأكيد, "
                "[رقم-رقم] للتصحيح, "
                "[s] لتخطي: "
            ).strip()
            
            if response == '':
                confirmed_tiles.append(result.tile)
                print(f"   ✅ تم تأكيد {result.tile}")
            
            elif response.lower() == 's':
                print(f"   ⏭️ تم تخطي")
            
            else:
                try:
                    nums = response.split('-')
                    a, b = int(nums[0]), int(nums[1])
                    corrected = DominoTile(a, b)
                    confirmed_tiles.append(corrected)
                    print(f"   ✏️ تم التصحيح إلى {corrected}")
                except (ValueError, IndexError):
                    print("   ❌ صيغة خاطئة، تم تخطي الحجر")
        
        # إضافة أحجار مفقودة
        print(
            "\nهل هناك أحجار لم يكتشفها النظام؟ "
            "(اكتب 'no' أو أدخل الأحجار)"
        )
        
        extra = input(">>> ").strip()
        if extra.lower() != 'no' and extra:
            parts = extra.split()
            for part in parts:
                try:
                    nums = part.split('-')
                    a, b = int(nums[0]), int(nums[1])
                    tile = DominoTile(a, b)
                    confirmed_tiles.append(tile)
                    print(f"  ➕ أُضيف: {tile}")
                except (ValueError, IndexError):
                    pass
        
        print(f"\n📦 الأحجار النهائية: {confirmed_tiles}")
        return confirmed_tiles
    
    @staticmethod
    def input_opponent_move(
        state: GameState
    ) -> Move:
        """
        إدخال حركة الخصم
        """
        current = state.current_turn
        name_map = {
            PlayerPosition.WEST: "اللاعب الغربي (يمينك)",
            PlayerPosition.NORTH: "الشريك (قدامك)",
            PlayerPosition.EAST: "اللاعب الشرقي (يسارك)"
        }
        
        print(f"\n🎯 دور: {name_map[current]}")
        print("[d] دق (pass)")
        print("[رقم-رقم L/R] لعب حجر (مثال: 6-4 L)")
        
        while True:
            response = input(">>> ").strip()
            
            if response.lower() == 'd':
                return Move(current, None, None)
            
            try:
                parts = response.split()
                nums = parts[0].split('-')
                a, b = int(nums[0]), int(nums[1])
                tile = DominoTile(a, b)
                
                direction = Direction.LEFT
                if len(parts) > 1:
                    if parts[1].upper() == 'R':
                        direction = Direction.RIGHT
                
                return Move(current, tile, direction)
            
            except (ValueError, IndexError):
                print("❌ صيغة خاطئة. حاول مرة أخرى")
