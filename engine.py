"""
محرك الذكاء الاصطناعي للعبة الداما الكلاسيكية (8x8 - 12 قطعة)
يستخدم خوارزمية Minimax مع بيئة محاكاة معزولة (Sandbox)
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
    """استثناء لإيقاف البحث فوراً وتجنب تجمد الواجهة"""
    pass

def get_legal_moves(board):
    if callable(board.legal_moves):
        return list(board.legal_moves())
    return list(board.legal_moves)

def get_board_fen(board):
    fen = board.fen
    return fen() if callable(fen) else fen

def parse_fen_pieces(fen_str):
    try:
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

    fen = get_board_fen(board)
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
    if deadline and time.time() > deadline:
        raise SearchTimeout()

    legal_moves = get_legal_moves(board)
    if depth == 0 or not legal_moves:
        return evaluate_position(board, ai_color)

    if maximizing:
        max_eval = -math.inf
        for move in legal_moves:
            board.push(move)
            score = minimax(board, depth - 1, alpha, beta, False, ai_color, deadline)
            board.pop()
            max_eval = max(max_eval, score)
            alpha = max(alpha, score)
            if beta <= alpha: break
        return max_eval
    else:
        min_eval = math.inf
        for move in legal_moves:
            board.push(move)
            score = minimax(board, depth - 1, alpha, beta, True, ai_color, deadline)
            board.pop()
            min_eval = min(min_eval, score)
            beta = min(beta, score)
            if beta <= alpha: break
        return min_eval

def find_best_move(original_board, ai_color, max_depth=5, time_limit=3.5):
    legal_moves = get_legal_moves(original_board)
    if not legal_moves: return None, 0, 0
    if len(legal_moves) == 1: return legal_moves[0], 0, 1
    
    best_move = legal_moves[0]
    best_score = -math.inf
    reached_depth = 0
    
    start_time = time.time()
    deadline = start_time + time_limit
    
    for depth in range(1, max_depth + 1):
        try:
            current_best_move = legal_moves[0]
            max_eval = -math.inf
            alpha = -math.inf
            beta = math.inf
            
            for move in legal_moves:
                sim_board = Board(variant="english", fen=get_board_fen(original_board))
                sim_move = None
                m_str = str(move)
                for sm in get_legal_moves(sim_board):
                    if str(sm) == m_str:
                        sim_move = sm
                        break
                
                if not sim_move: 
                    sim_move = get_legal_moves(sim_board)[0]
                
                sim_board.push(sim_move)
                score = minimax(sim_board, depth - 1, alpha, beta, False, ai_color, deadline)
                
                if score > max_eval:
                    max_eval = score
                    current_best_move = move
                
                alpha = max(alpha, score)
            
            best_move = current_best_move
            best_score = max_eval
            reached_depth = depth
            
            if abs(best_score) > 90000: break
                
        except SearchTimeout:
            break
            
    return best_move, best_score, reached_depth
