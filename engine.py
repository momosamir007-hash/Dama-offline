"""
محرك الذكاء الاصطناعي للعبة الداما الكلاسيكية (8x8 - 12 قطعة)
يستخدم خوارزمية Minimax مع Alpha-Beta Pruning و Iterative Deepening
"""
import math
import time

try:
    from draughts import Board, WHITE, BLACK
    DRAUGHTS_AVAILABLE = True
except ImportError:
    DRAUGHTS_AVAILABLE = False
    WHITE, BLACK = 2, 1

KING_VALUE = 50
PIECE_VALUE = 10
CENTER_BONUS = 1.0
ADVANCEMENT_BONUS = 0.5
MOBILITY_WEIGHT = 0.3
BACK_ROW_BONUS = 0.8

CENTER_SQUARES = {10, 11, 14, 15, 18, 19, 22, 23}
INNER_CENTER = {14, 15, 18, 19}
WHITE_BACK_ROW = {29, 30, 31, 32}
BLACK_BACK_ROW = {1, 2, 3, 4}

class SearchTimeout(Exception):
    """استثناء لإيقاف البحث فوراً عند تجاوز الوقت المحدد"""
    pass

def get_legal_moves(board):
    if callable(board.legal_moves):
        return list(board.legal_moves())
    return list(board.legal_moves)

def parse_fen_pieces(fen_str):
    try:
        if callable(fen_str):
            fen_str = fen_str()
        parts = fen_str.split(':')
        if len(parts) < 3: return [], []
        white_str = parts[1][1:] if len(parts[1]) > 1 else ""
        black_str = parts[2][1:] if len(parts[2]) > 1 else ""
        white_pieces, black_pieces = [], []
        for p in white_str.split(','):
            p = p.strip()
            if not p: continue
            if p.startswith('K'):
                try: white_pieces.append((int(p[1:]), True))
                except ValueError: pass
            else:
                try: white_pieces.append((int(p), False))
                except ValueError: pass
        for p in black_str.split(','):
            p = p.strip()
            if not p: continue
            if p.startswith('K'):
                try: black_pieces.append((int(p[1:]), True))
                except ValueError: pass
            else:
                try: black_pieces.append((int(p), False))
                except ValueError: pass
        return white_pieces, black_pieces
    except Exception: return [], []

def evaluate_position(board, ai_color):
    legal_moves = get_legal_moves(board)
    if not legal_moves:
        return -100000 if board.turn == ai_color else 100000

    fen = board.fen if isinstance(board.fen, str) else board.fen()
    white_pieces, black_pieces = parse_fen_pieces(fen)
    if not white_pieces and not black_pieces:
        return len(legal_moves) if board.turn == ai_color else -len(legal_moves)
        
    white_score = _score_side(white_pieces, is_white=True)
    black_score = _score_side(black_pieces, is_white=False)
    mobility = len(legal_moves) * MOBILITY_WEIGHT

    base = white_score - black_score if ai_color == WHITE else black_score - white_score
    base += mobility if board.turn == ai_color else -mobility
    return base

def _score_side(pieces, is_white):
    score = 0.0
    for sq, is_king in pieces:
        if is_king:
            score += KING_VALUE
            if sq in INNER_CENTER: score += CENTER_BONUS * 1.5
            elif sq in CENTER_SQUARES: score += CENTER_BONUS
        else:
            score += PIECE_VALUE
            row = (sq - 1) // 4
            advancement = 7 - row if is_white else row
            score += advancement * ADVANCEMENT_BONUS
            if sq in INNER_CENTER: score += CENTER_BONUS * 1.2
            elif sq in CENTER_SQUARES: score += CENTER_BONUS * 0.8
            back_row = WHITE_BACK_ROW if is_white else BLACK_BACK_ROW
            if sq in back_row: score += BACK_ROW_BONUS
    return score

def minimax(board, depth, alpha, beta, maximizing, ai_color, deadline=None):
    # إيقاف فوري يمنع تجمد الواجهة
    if deadline and time.time() > deadline:
        raise SearchTimeout()

    legal_moves = get_legal_moves(board)
    if depth == 0 or not legal_moves:
        return evaluate_position(board, ai_color), None

    best_move = legal_moves[0]
    if maximizing:
        max_eval = -math.inf
        for move in legal_moves:
            board.push(move)
            score, _ = minimax(board, depth - 1, alpha, beta, False, ai_color, deadline)
            board.pop()
            if score > max_eval:
                max_eval = score
                best_move = move
            alpha = max(alpha, score)
            if beta <= alpha: break
        return max_eval, best_move
    else:
        min_eval = math.inf
        for move in legal_moves:
            board.push(move)
            score, _ = minimax(board, depth - 1, alpha, beta, True, ai_color, deadline)
            board.pop()
            if score < min_eval:
                min_eval = score
                best_move = move
            beta = min(beta, score)
            if beta <= alpha: break
        return min_eval, best_move

def get_clean_move(original_board, target_move):
    legal_moves = get_legal_moves(original_board)
    if not legal_moves: return None
    target_str = str(target_move)
    for m in legal_moves:
        if str(m) == target_str:
            return m
    for m in legal_moves:
        try:
            if hasattr(m, 'pdn_move') and hasattr(target_move, 'pdn_move') and m.pdn_move == target_move.pdn_move: return m
        except Exception: pass
    return legal_moves[0]

def find_best_move(original_board, ai_color, max_depth=5, time_limit=4.0):
    original_moves = get_legal_moves(original_board)
    if not original_moves: return None, 0, 0
    if len(original_moves) == 1: return original_moves[0], 0, 1
    
    search_board = original_board.copy()
    start_time = time.time()
    deadline = start_time + time_limit
    
    best_move = original_moves[0]
    best_score = 0
    reached_depth = 0
    
    for depth in range(1, max_depth + 1):
        try:
            score, move = minimax(search_board, depth, -math.inf, math.inf, True, ai_color, deadline)
            if move is not None:
                best_move = move
                best_score = score
                reached_depth = depth
        except SearchTimeout:
            break # إيقاف بأمان بسبب انتهاء الوقت
        except Exception: 
            break
            
        if abs(best_score) > 90000: break
            
    clean_move = get_clean_move(original_board, best_move)
    return clean_move, best_score, reached_depth
