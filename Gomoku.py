#!/usr/bin/env python3
import time  # Import time module for delay
import sys
import random
import logging
import math

if sys.platform == "win32":
    # If on Windows, check if windows-curses is installed (if it works, we import `curses` rather than importing `windows-curses`)
    try:
        import curses
    except ImportError:
    # If on Windows and window-curses not installed, raise an exception and tell the user
        print("On Windows, install the 'windows-curses' package.")
        raise
else:
    import curses

# Configure logging to help debug AI behavior
logging.basicConfig(
    filename='gomoku_ai_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define board size and piece representations
BOARD_SIZE = 15
WHITE_PIECE = 'W'
BLACK_PIECE = 'B'
EMPTY = '.'

# Define directions for later checking: right, down, diagonal down-right, diagonal down-left
DIRECTIONS = [(1, 0), (0, 1), (1, 1), (-1, 1)]

# Time limit for AI search in seconds
TIME_LIMIT = 10

# AI search radius for possible moves
SEARCH_RADIUS = 2

# AI search depth for minimax
DEPTH = 4

# Initialize an empty game board
board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
cursor_x, cursor_y = BOARD_SIZE // 2, BOARD_SIZE // 2 # start in the middle
turn = WHITE_PIECE  # White player starts

# Zobrist Hashing (if needed for further optimizations)
# Table indexing is ZOBRIST_TABLE[y][x][p], where p = 0 for white and p = 1 for black
ZOBRIST_TABLE = [[[random.getrandbits(64) for _ in range(2)] for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
trans_table = {}
board_hash = 0

# Define Pattern Dictionary for AI Evaluation
def create_pattern_dict():
    """
    Creates a dictionary of patterns for evaluating the board state in Gomoku.
    Patterns are scored based on their potential to create a winning sequence.

    Scoring Details:
        - Positive scores favor the AI (maximizing player).
        - Negative scores penalize patterns favorable to the opponent (minimizing player).
        - Higher scores are assigned to more advanced or threatening patterns.

    Patterns:
        - `1` represents the AI's pieces.
        - `-1` represents the opponent's pieces.
        - `0` represents empty spaces.

    Returns:
        pattern_dict (dict): A dictionary where keys are patterns (tuples) and values are their corresponding scores.
    """
    pattern_dict = {}
    # Patterns for both players
    for x in [-1, 1]:  # -1 for opponent, 1 for AI
        y = -x
        # Five-in-a-row (Victory)
        pattern_dict[(x, x, x, x, x)]       = math.inf * x
        # Open-ended four-in-a-row
        pattern_dict[(0, x, x, x, x, 0)]    = 100000 * x
        # One-and-Three
        pattern_dict[(0, x, 0, x, x, x, 0)] = 50000 * x
        pattern_dict[(0, x, x, x, 0, x, 0)] = 50000 * x
        # Two-and-Two
        pattern_dict[(0, x, x, 0, x, x, 0)] = 25000 * x
        # Half-closed four-in-a-row (blocked on one end)
        pattern_dict[(0, x, x, x, x, y)]    = 10000 * x
        pattern_dict[(y, x, x, x, x, 0)]    = 10000 * x
        # Fully closed four-in-a-row (blocked on both ends)
        pattern_dict[(y, x, x, x, x, y)]    = -1000 * x
        # Open-ended three-in-a-row (potential to form four-in-a-row)
        pattern_dict[(0, x, x, x, 0)]       = 5000 * x
        pattern_dict[(y, x, x, x, 0)]       = 1000 * x
        pattern_dict[(0, x, x, x, y)]       = 1000 * x
        # One-and-Two
        pattern_dict[(0, x, 0, x, x, 0)]    = 1000 * x
        pattern_dict[(0, x, x, 0, x, 0)]    = 1000 * x
        # Open-ended two-in-a-row (early game potential)
        pattern_dict[(0, 0, x, x, 0)]       = 100 * x
    return pattern_dict

def get_possible_pattern_lengths(pattern_dict: dict):
    possible_lengths: set[int] = set()

    for key in pattern_dict:
        possible_lengths.add(len(key))

    return possible_lengths


# Generate the global pattern dictionary
PATTERN_DICT = create_pattern_dict()

POSSIBLE_PATTERN_LENGTHS = get_possible_pattern_lengths(PATTERN_DICT)

MAX_PATTERN_LENGTH = max(POSSIBLE_PATTERN_LENGTHS)

def print_banner():
    """
    Displays the game banner with version and author information.
    """
    banner = r"""
  ________                       __
 /  _____/  ____   _____   ____ |  | ____ __
/   \  ___ /  _ \ /     \ /  _ \|  |/ /  |  \
\    \_\  (  <_> )  Y Y  (  <_> )    <|  |  /
 \______  /\____/|__|_|  /\____/|__|_ \____/
        \/             \/            \/
                                Version: 0.11

Authors:
Leung Wang Chan(lchan2021@csu.fullerton.edu)
Tung Le (giatung2002@csu.fullerton.edu)
Kyle Ho (kyleho@csu.fullerton.edu)

"""
    print(banner)

def show_menu():
    """
    Displays the game mode selection menu to the user.

    Returns:
        game_mode (str): The selected game mode ('pvp' or 'ai').
    """
    print("\nChoose your game mode:")
    print("1. Player vs Player (PVP)")
    print("2. Play with AI")
    print("Enter 'quit' to terminate the program.")

    while True:
        choice = input("\nEnter your choice (1/2) or 'quit': ").strip().lower()

        if choice == '1':
            return "pvp"
        elif choice == '2':
            return "ai"
        elif choice == 'quit':
            print("Exiting the program. Goodbye!")
            exit(0)
        else:
            print("Invalid choice. Please enter '1', '2', or 'quit'.")

def print_board(stdscr: curses.window):
    """
    Renders the game board on the screen using curses.

    Args:
        stdscr: The curses window object.
    """
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    required_height = BOARD_SIZE + 6  # Rows needed for the board and additional text
    required_width = BOARD_SIZE * 2 + 2  # Columns needed for the board display

    # Check if the terminal window is large enough to display the board
    if height < required_height or width < required_width:
        error_msg = f"Terminal too small. Requires at least {required_height} rows and {required_width} columns."
        try:
            stdscr.addstr(0, 0, error_msg, curses.A_BOLD)
        except curses.error:
            pass  # In case the terminal is too small to display the error message
        stdscr.refresh()
        stdscr.getch()
        sys.exit(1)

    # Display game title and instructions
    stdscr.addstr(0, 0, "Gomoku V0.11", curses.A_BOLD)
    stdscr.addstr(2, 0, "Use arrow keys to move. Press 'w' to place White, 'b' to place Black. 'q' to quit.")

    # Draw the board with cursor
    for y in range(BOARD_SIZE): # Loop over each row of the board
        for x in range(BOARD_SIZE): # Loop over each column in the current row
            if x == cursor_x and y == cursor_y:
                # If the current board position matches the cursor position
                # Display the board cell with reverse colors to highlight the cursor
                stdscr.addstr(y + 4, x * 2, board[y][x], curses.A_REVERSE)  # Highlight the cursor position
            else:
                # If this position is not the cursor, display it normally
                stdscr.addstr(y + 4, x * 2, board[y][x])
            # Display the current player's turn below the board
    stdscr.addstr(BOARD_SIZE + 5, 0, f"Current turn: {'White' if turn == WHITE_PIECE else 'Black'}")
    stdscr.refresh()# Refresh the screen to show all updates

    # Draw the board with cursor highlighting
    for y in range(BOARD_SIZE):  # Loop over each row of the board
        for x in range(BOARD_SIZE):  # Loop over each column in the current row
            try:
                if x == cursor_x and y == cursor_y:
                    # Highlight the cursor position with reverse video
                    stdscr.addstr(y + 4, x * 2, board[y][x], curses.A_REVERSE)
                else:
                    stdscr.addstr(y + 4, x * 2, board[y][x])
            except curses.error:
                pass  # Ignore if trying to write outside the window

    # Display the current player's turn below the board
    try:
        stdscr.addstr(BOARD_SIZE + 5, 0, f"Current turn: {'White' if turn == WHITE_PIECE else 'Black'}", curses.A_UNDERLINE)
    except curses.error:
        pass  # Ignore if out of bounds

    stdscr.refresh()  # Refresh the screen to show all updates

def place_piece(x: int, y: int, player: str):
    """
    Places a piece on the board and updates the hash value

    Args:
        x, y: Coordinates of the piece
        player: The player placing the piece ('W' or 'B')

    Returns None

    """
    global board_hash

    piece = 0 if player == WHITE_PIECE else 1
    board[y][x] = player
    board_hash ^= ZOBRIST_TABLE[y][x][piece]
    return

def undo_piece(x: int, y: int):
    """
    Undoes a piece placement on the board and updates the hash value

    Args:
        x, y: Coordinates of the piece

    Returns None

    """
    global board_hash

    piece = 0 if board[y][x] == WHITE_PIECE else 1
    board[y][x] = EMPTY
    board_hash ^= ZOBRIST_TABLE[y][x][piece]
    return

def check_winner(board: list[list[str]]):
    """
    Checks the board for a winner by looking for five consecutive pieces.

    Args:
        board: The current game board.

    Returns:
        The piece type of the winner ('W' or 'B') if a winner is found, else None.
    """
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] == EMPTY:
                continue  # Skip empty cells
            for dx, dy in DIRECTIONS:
                count = 0  # Initialize count of consecutive pieces
                for i in range(5):
                    nx, ny = x + i * dx, y + i * dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == board[y][x]:
                        count += 1
                    else:
                        break
                if count == 5:
                    return board[y][x]  # Winner found
    return None  # No winner

def evaluate_board(board: list[list[str]], player: str):
    """
    Evaluate the board and return a score based on the current player's advantage.

    Positive scores indicate favorability towards the AI player.
    Negative scores indicate favorability towards the opponent.

    Args:
        board: The current game board.
        player: The AI player's piece type ('W' or 'B').

    Returns:
        score (int): The evaluated score of the board.
    """
    score = 0  # Initialize the score to 0
    opponent = WHITE_PIECE if player == BLACK_PIECE else BLACK_PIECE

    global trans_table
    temp_hash = 0
    piece = 0 if player == WHITE_PIECE else 1
    opponent_piece = 1 if player == WHITE_PIECE else 0

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] == player:
                temp_hash ^= ZOBRIST_TABLE[y][x][piece]
            elif board[y][x] == opponent:
                temp_hash ^= ZOBRIST_TABLE[y][x][opponent_piece]

    if temp_hash in trans_table:
        logging.debug(f'Position already in transposition table, in evaluate_board')
        return trans_table[temp_hash]

    # Iterate through all cells and evaluate patterns
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            for dx, dy in DIRECTIONS:
                pattern = []
                for i in range(MAX_PATTERN_LENGTH):
                    nx, ny = x + i * dx, y + i * dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        piece = board[ny][nx]
                        if piece == player:
                            pattern.append(1)
                        elif piece == opponent:
                            pattern.append(-1)
                        else:
                            pattern.append(0)
                    else:
                        pattern.append(-1)  # Out of bounds
                        break
                    if (i + 1) in POSSIBLE_PATTERN_LENGTHS: # If current length is in POSSIBLE_PATTERN_LENGTHS
                        pattern_tuple = tuple(pattern)
                        if pattern_tuple in PATTERN_DICT:
                            score += PATTERN_DICT[pattern_tuple]
    logging.debug(f'Evaluate Board Score for player {player}: {score}')  # Log the evaluation score
    trans_table[temp_hash] = score
    return score

def evaluate_move_position(board: list[list[str]], x: int, y: int, player: str):
    """
    Heuristic to evaluate the desirability of a move position.
    Positive scores indicate favorable positions for the player.
    Negative scores indicate unfavorable positions.

    Args:
        board: The current game board.
        x (int): The x-coordinate of the move.
        y (int): The y-coordinate of the move.
        player (str): The player's piece type ('W' or 'B').

    Returns:
        score (int): The evaluated score of the move position.
    """

    score = 0
    opponent = WHITE_PIECE if player == BLACK_PIECE else BLACK_PIECE

    for dx, dy in DIRECTIONS:
        for i in range(1, 5):  # Check four steps in each direction
            nx, ny = x + dx * i, y + dy * i
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                if board[ny][nx] == player:
                    score += 2  # Friendly piece found
                elif board[ny][nx] == opponent:
                    score += 1  # Opponent's piece found
                else:
                    break  # Empty space encountered
            else:
                score -= 1  # Out of bounds
    return score

def minimax(board: list[list[str]], depth: int, is_maximizing: bool, player: str,
            alpha: float, beta: float, start_time: float, last_move: tuple[int, int]):
    """
    Minimax algorithm with alpha-beta pruning and time constraint.

    Args:
        board: The current game board.
        depth (int): The current depth in the game tree.
        is_maximizing (bool): True if the current layer is maximizing, False otherwise.
        player (str): The AI player's piece type ('W' or 'B').
        alpha (float): The alpha value for pruning.
        beta (float): The beta value for pruning.
        start_time (float): The start time of the search.
        last_move (tuple): The last move made (x, y).

    Returns:
        score (int): The evaluated score of the board.
    """

    global trans_table

    if time.time() - start_time > TIME_LIMIT:
        logging.debug("Time limit exceeded during minimax search.")
        return evaluate_board(board, player)

    winner = check_winner(board)
    if winner == player:
        return math.inf  # AI wins
    elif winner is not None:
        return -math.inf  # Opponent wins

    if depth == 0:
        return evaluate_board(board, player)

    lx, ly = last_move
    possible_moves: list[tuple[tuple[int, int], int]] = []

    # Generate possible moves within the search radius
    for y in range(max(0, ly - SEARCH_RADIUS), min(BOARD_SIZE, ly + SEARCH_RADIUS + 1)):
        for x in range(max(0, lx - SEARCH_RADIUS), min(BOARD_SIZE, lx + SEARCH_RADIUS + 1)):
            if board[y][x] == EMPTY:
                move_score = evaluate_move_position(board, x, y, player)
                possible_moves.append(((x, y), move_score))

    # Sort moves based on heuristic score to improve pruning effectiveness
    possible_moves.sort(key=lambda move: move[1], reverse=True)

    if is_maximizing:
        best_score = -math.inf
        for move, _ in possible_moves:
            x, y = move
            place_piece(x, y, player)
            if board_hash not in trans_table:
                score = minimax(board, depth - 1, False, player, alpha, beta, start_time, (x, y))
                trans_table[board_hash] = score
            else:
                score = trans_table[board_hash]
                logging.debug(f'Position already in transposition table, in maximizing layer')
            undo_piece(x, y)
            best_score = max(best_score, score)
            if best_score >= beta:
                logging.debug("Alpha-beta pruning activated in maximizing layer.")
                break  # Beta cutoff
            alpha = max(alpha, best_score)
    else:
        opponent = WHITE_PIECE if player == BLACK_PIECE else BLACK_PIECE
        best_score = math.inf
        for move, _ in possible_moves:
            x, y = move
            place_piece(x, y, opponent)
            if board_hash not in trans_table:
                score = minimax(board, depth - 1, True, player, alpha, beta, start_time, (x, y))
                trans_table[board_hash] = score
            else:
                score = trans_table[board_hash]
                logging.debug(f'Position already in transposition table, in minimizing layer')
            undo_piece(x, y)
            best_score = min(best_score, score)
            if best_score <= alpha:
                logging.debug("Alpha-beta pruning activated in minimizing layer.")
                break  # Alpha cutoff
            beta = min(beta, best_score)

    return best_score

def get_ai_move(board: list[list[str]], player: str, last_move: tuple):
    """
    Determines the best move for the AI player using the minimax algorithm with alpha-beta pruning.

    Args:
        board: The current game board.
        player (str): The AI player's piece type ('W' or 'B').
        last_move (tuple): The last move made (x, y).

    Returns:
        best_move (tuple): The coordinates (x, y) of the best move.
    """

    global trans_table

    best_move = None
    best_score = -math.inf
    start_time = time.time()
    alpha = -math.inf
    beta = math.inf
    lx, ly = last_move

    possible_moves: list[tuple[tuple[int, int], int]] = []

    # Generate possible moves within the search radius
    for y in range(max(0, ly - SEARCH_RADIUS), min(BOARD_SIZE, ly + SEARCH_RADIUS + 1)):
        for x in range(max(0, lx - SEARCH_RADIUS), min(BOARD_SIZE, lx + SEARCH_RADIUS + 1)):
            if board[y][x] == EMPTY:
                move_score = evaluate_move_position(board, x, y, player)
                possible_moves.append(((x, y), move_score))

    # Sort moves based on heuristic score to prioritize better moves
    possible_moves.sort(key=lambda move: move[1], reverse=True)

    for move, _ in possible_moves:
        if time.time() - start_time > TIME_LIMIT:
            if not best_move:
                logging.debug("No best move chosen. Selecting best move by heuristic")
                return possible_moves[0][0]
            logging.debug("Time limit exceeded before completing all move evaluations.")
            break

        x, y = move
        place_piece(x, y, BLACK_PIECE)
        if board_hash not in trans_table:
            score = minimax(board, depth=DEPTH, is_maximizing=False, player=player, alpha=alpha, beta=beta,
                       start_time=start_time, last_move=(x, y))
            trans_table[board_hash] = score
        else:
            score = trans_table[board_hash]
            logging.debug(f'Position already in transposition table, in get_ai_move')
        undo_piece(x, y)

        logging.debug(f'AI evaluating move at ({x}, {y}) with score {score}')

        if score > best_score:
            best_score = score
            best_move = (x, y)
            alpha = max(alpha, best_score)  # Update alpha for pruning

    logging.info(f'AI selected move: {best_move} with score {best_score}')
    logging.info(f'AI took {time.time() - start_time} seconds to select move')

    return best_move

def main(stdscr: curses.window, game_mode: str):
    """
    The main game loop handling user input, AI moves, and game state updates.

    Args:
        stdscr: The curses window object.
        game_mode (str): The selected game mode ('pvp' or 'ai').
    """
    global cursor_x, cursor_y, turn
    last_player_move = (7, 7)  # Initialize last_player_move to center

    # Setup curses settings
    curses.curs_set(0)  # Hide the default cursor
    stdscr.keypad(True)  # Enable special keys (like arrow keys) to be read directly
    stdscr.clear()  # Clear the screen to start fresh
    stdscr.refresh()  # Apply the clear to the display

    # Display initial board and instructions
    print_board(stdscr)

    while True:  # Main game loop

        if game_mode == "ai" and turn == BLACK_PIECE:  # AI's turn
            ai_move = get_ai_move(board, BLACK_PIECE, last_player_move)  # Get AI's move
            if ai_move:  # If the AI returned a valid move
                x, y = ai_move
                place_piece(x, y, BLACK_PIECE)
                last_player_move = (x, y)  # Update last_player_move
                winner = check_winner(board)
                logging.debug(f'AI placed at ({x}, {y}). Current board state:')
                for row in board:
                    logging.debug(' '.join(row))
                if winner == BLACK_PIECE:
                    print_board(stdscr)
                    try:
                        stdscr.addstr(BOARD_SIZE + 6, 0, "Black (AI) wins!", curses.A_BOLD)
                    except curses.error:
                        pass  # Ignore if out of bounds
                    stdscr.refresh()
                    stdscr.getch()
                    break
                turn = WHITE_PIECE  # Switch turn to White
                print_board(stdscr)
                continue  # Continue to next iteration
            else:
                logging.debug(f'AI found no valid move.')
                break


        try:
            key = stdscr.getch()  # Wait for user input
        except KeyboardInterrupt:
            break  # Allow graceful exit on Ctrl+C

        # Handle quit command
        if key == ord('q'):
            break

        # Movement commands using arrow keys
        elif key == curses.KEY_RIGHT:
            cursor_x = (cursor_x + 1) % BOARD_SIZE
        elif key == curses.KEY_LEFT:
            cursor_x = (cursor_x - 1) % BOARD_SIZE
        elif key == curses.KEY_DOWN:
            cursor_y = (cursor_y + 1) % BOARD_SIZE
        elif key == curses.KEY_UP:
            cursor_y = (cursor_y - 1) % BOARD_SIZE

        # Initialize last player move to cursor position
        last_player_move = (cursor_x, cursor_y)

        # Place a White piece if it's White's turn
        if key == ord('w') and turn == WHITE_PIECE:
            if board[cursor_y][cursor_x] == EMPTY:
                place_piece(cursor_x, cursor_y, WHITE_PIECE)
                last_player_move = (cursor_x, cursor_y)
                winner = check_winner(board)
                logging.debug(f'Player (White) placed at ({cursor_x}, {cursor_y}). Current board state:')
                for row in board:
                    logging.debug(' '.join(row))
                if winner == WHITE_PIECE:
                    print_board(stdscr)
                    try:
                        stdscr.addstr(BOARD_SIZE + 6, 0, "White wins!", curses.A_BOLD)
                    except curses.error:
                        pass  # Ignore if out of bounds
                    stdscr.refresh()
                    stdscr.getch()
                    break
                turn = BLACK_PIECE  # Switch turn to Black

        # Place a Black piece if it's Black's turn in PvP mode
        if game_mode == "pvp" and key == ord('b') and turn == BLACK_PIECE:
            if board[cursor_y][cursor_x] == EMPTY:
                place_piece(cursor_x, cursor_y, BLACK_PIECE)
                last_player_move = (cursor_x, cursor_y)
                winner = check_winner(board)
                logging.debug(f'Player (Black) placed at ({cursor_x}, {cursor_y}). Current board state:')
                for row in board:
                    logging.debug(' '.join(row))
                if winner == BLACK_PIECE:
                    print_board(stdscr)
                    try:
                        stdscr.addstr(BOARD_SIZE + 6, 0, "Black wins!", curses.A_BOLD)
                    except curses.error:
                        pass  # Ignore if out of bounds
                    stdscr.refresh()
                    stdscr.getch()
                    break
                turn = WHITE_PIECE  # Switch turn to White

        # Refresh the board display after each action
        print_board(stdscr)

# Run the banner and curses wrapper to initiate the main loop
if __name__ == "__main__":
    print_banner()
    game_mode = show_menu()
    print(f"Selected game mode: {'Player vs Player' if game_mode == 'pvp' else 'Play with AI'}")
    curses.wrapper(main, game_mode)
