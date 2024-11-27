#!/usr/bin/env python3
import time  # Import time module for delay
import sys
import random
import logging

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
DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)] # Directions: right, down, diagonal down-right, diagonal up-right

# Initialize an empty game board
board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
cursor_x, cursor_y = BOARD_SIZE // 2, BOARD_SIZE // 2 # start in the middle
turn = WHITE_PIECE  # White player starts

# Zobrist Hashing (if needed for further optimizations)
ZOBRIST_TABLE = [[[random.getrandbits(64) for _ in range(2)] for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
TRANS_TABLE = {}

# Define Pattern Dictionary for AI Evaluation
def create_pattern_dict():
    """
    Creates a dictionary of patterns for evaluating the board state in Gomoku.
    Patterns are scored based on their potential to create a winning sequence.

    Returns:
        pattern_dict (dict): A dictionary where keys are patterns (tuples) and values are their corresponding scores.
    """
    pattern_dict = {}
    # Patterns for both players
    for player in [-1, 1]:  # -1 for opponent, 1 for AI
        # Five in a row
        pattern_dict[tuple([player]*5)] = 1000000 * player
        # Open-ended four
        pattern_dict[tuple([0, player]*4 + [0])] = 100000 * player
        # Closed four
        pattern_dict[tuple([player]*4 + [0])] = 10000 * player
        # Open-ended three
        pattern_dict[tuple([0, player]*3 + [0])] = 1000 * player
        # Closed three
        pattern_dict[tuple([player]*3 + [0])] = 100 * player
    return pattern_dict

# Generate the global pattern dictionary
PATTERN_DICT = create_pattern_dict()

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

    # Iterate through all cells and evaluate patterns
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            for dx, dy in DIRECTIONS:
                pattern = []
                for i in range(5):  # Only patterns of length 5 are considered
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
                        pattern.append(-99)  # Out of bounds
                pattern_tuple = tuple(pattern)
                if pattern_tuple in PATTERN_DICT:
                    score += PATTERN_DICT[pattern_tuple]
    logging.debug(f'Evaluate Board Score for player {player}: {score}')  # Log the evaluation score
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
        count = 0
        for i in range(1, 3):  # Check two steps in each direction
            nx, ny = x + dx * i, y + dy * i
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                if board[ny][nx] == player:
                    count += 1  # Friendly piece found
                elif board[ny][nx] == opponent:
                    count -= 1  # Opponent's piece found
                else:
                    break  # Empty space encountered
            else:
                count -= 1  # Out of bounds
        score += count
    return score

def minimax(board: list[list[str]], depth: int, is_maximizing: bool, player: str,
            alpha: float, beta: float, start_time: float, time_limit: int, last_move: tuple):
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
        time_limit (int): The time limit for the search in seconds.
        last_move (tuple): The last move made (x, y).

    Returns:
        score (int): The evaluated score of the board.
    """
    if time.time() - start_time > time_limit:
        logging.debug("Time limit exceeded during minimax search.")
        return evaluate_board(board, player)

    winner = check_winner(board)
    if winner == player:
        return 100000  # AI wins
    elif winner is not None:
        return -100000  # Opponent wins

    if depth == 0:
        return evaluate_board(board, player)

    lx, ly = last_move
    search_radius = 2  # Define the search radius around the last move
    possible_moves = []

    # Generate possible moves within the search radius
    for y in range(max(0, ly - search_radius), min(BOARD_SIZE, ly + search_radius + 1)):
        for x in range(max(0, lx - search_radius), min(BOARD_SIZE, lx + search_radius + 1)):
            if board[y][x] == EMPTY:
                move_score = evaluate_move_position(board, x, y, player)
                possible_moves.append(((x, y), move_score))

    # Sort moves based on heuristic score to improve pruning effectiveness
    possible_moves.sort(key=lambda move: move[1], reverse=True)

    if is_maximizing:
        best_score = -float('inf')
        for move, _ in possible_moves:
            x, y = move
            board[y][x] = player  # Make the move
            score = minimax(board, depth - 1, False, player, alpha, beta, start_time, time_limit, (x, y))
            board[y][x] = EMPTY  # Undo the move
            best_score = max(best_score, score)
            alpha = max(alpha, best_score)
            if beta <= alpha:
                logging.debug("Alpha-beta pruning activated in maximizing layer.")
                break  # Beta cutoff
        return best_score
    else:
        opponent = WHITE_PIECE if player == BLACK_PIECE else BLACK_PIECE
        best_score = float('inf')
        for move, _ in possible_moves:
            x, y = move
            board[y][x] = opponent  # Make the opponent's move
            score = minimax(board, depth - 1, True, player, alpha, beta, start_time, time_limit, (x, y))
            board[y][x] = EMPTY  # Undo the move
            best_score = min(best_score, score)
            beta = min(beta, best_score)
            if beta <= alpha:
                logging.debug("Alpha-beta pruning activated in minimizing layer.")
                break  # Alpha cutoff
        return best_score

def get_ai_move(board: list[list[str]], player: str, last_move: tuple, time_limit=10):
    """
    Determines the best move for the AI player using the minimax algorithm with alpha-beta pruning.

    Args:
        board: The current game board.
        player (str): The AI player's piece type ('W' or 'B').
        last_move (tuple): The last move made (x, y).
        time_limit (int): The time limit for the AI to decide on a move in seconds.

    Returns:
        best_move (tuple): The coordinates (x, y) of the best move.
    """
    best_move = None
    best_score = -float('inf')
    start_time = time.time()
    alpha = -float('inf')
    beta = float('inf')
    lx, ly = last_move
    search_radius = 2  # Define the search radius around the last move

    possible_moves = []

    # Generate possible moves within the search radius
    for y in range(max(0, ly - search_radius), min(BOARD_SIZE, ly + search_radius + 1)):
        for x in range(max(0, lx - search_radius), min(BOARD_SIZE, lx + search_radius + 1)):
            if board[y][x] == EMPTY:
                move_score = evaluate_move_position(board, x, y, player)
                possible_moves.append(((x, y), move_score))

    # Sort moves based on heuristic score to prioritize better moves
    possible_moves.sort(key=lambda move: move[1], reverse=True)

    for move, _ in possible_moves:
        if time.time() - start_time > time_limit:
            logging.debug("Time limit exceeded before completing all move evaluations.")
            break

        x, y = move
        board[y][x] = player  # Make the move
        score = minimax(board, depth=4, is_maximizing=False, player=player, alpha=alpha, beta=beta,
                       start_time=start_time, time_limit=time_limit, last_move=(x, y))
        board[y][x] = EMPTY  # Undo the move

        logging.debug(f'AI evaluating move at ({x}, {y}) with score {score}')

        if score > best_score:
            best_score = score
            best_move = (x, y)
            alpha = max(alpha, best_score)  # Update alpha for pruning

    logging.info(f'AI selected move: {best_move} with score {best_score}')
    return best_move

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
            ai_move = get_ai_move(board, BLACK_PIECE, last_player_move, time_limit=10)  # Get AI's move
            if ai_move:  # If the AI returned a valid move
                x, y = ai_move
                board[y][x] = BLACK_PIECE  # Place the Black piece on the board
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
                board[cursor_y][cursor_x] = WHITE_PIECE
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
                board[cursor_y][cursor_x] = BLACK_PIECE
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
