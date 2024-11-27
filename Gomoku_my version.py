#!/usr/bin/env python3
import time  # Import time module for delay
import sys
import random

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

# Define board size and initial settings
BOARD_SIZE = 15
WHITE_PIECE = 'W'
BLACK_PIECE = 'B'
EMPTY = '.'

# Initialize an empty game board
board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
cursor_x, cursor_y = BOARD_SIZE // 2, BOARD_SIZE // 2 # start in the middle
turn = WHITE_PIECE  # White player starts


# Zobrist Hashing
ZOBRIST_TABLE = [[[random.getrandbits(64) for _ in range(2)] for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
TRANS_TABLE = {}


def print_banner():
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
Kyle Ho (kyleho@csu.fullerton.edu)

"""
    print(banner)


def print_board(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "Gomoku V0.11")
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

def check_winner(board):
    # Check all rows, columns, and diagonals for a five-in-a-row sequence
    # directions defines movements: (1, 0) -> right, (0, 1) -> down,
    # (1, 1) -> diagonal down-right, (1, -1) -> diagonal up-right.
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]

    # Iterate over every cell in the board
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            # Skip empty cells as they cannot be the start of a winning line
            if board[y][x] == EMPTY:
                continue
                # Check each direction from the current cell
            for dx, dy in directions:
                count = 0 # Initialize count of consecutive pieces
                # Check up to 5 cells in the current direction
                for i in range(5):
                    nx, ny = x + i * dx, y + i * dy # Calculate the next cell in the direction
                    # Verify that the cell is within bounds and matches the initial cell's piece
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == board[y][x]:
                        count += 1 # Increment the count if the piece matches
                    else:
                        break # Stop checking this direction if out of bounds or piece does not match
                # If 5 consecutive pieces are found, return the piece type as the winner
                if count == 5:
                    return board[y][x]
    # If no winner found after checking all cells, return None
    return None


# Pattern Scoring
def create_pattern_dict():
    """
    Create a dictionary of patterns for evaluating the board state in Gomoku.
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
    pattern_dict (dict): A dictionary where keys are patterns (tuples) and  values are their corresponding scores.
    """
    pattern_dict = {}
    x = -1 # Start with the opponent's perspective (-1 for opponent pieces)
    while x < 2: # Loop to generate patterns for both players (-1 and 1)
        y = -x # Set `y` as the opposite player's piece value
        pattern_dict[(x, x, x, x, x)] = 1000000 * x # Five consecutive pieces (winning condition)
        pattern_dict[(0, x, x, x, x, 0)] = 100000 * x # Open-ended four-in-a-row (high threat, both ends open)
        pattern_dict[(0, x, x, x, 0, x, 0)] = 100000 * x # Variations of open-ended four-in-a-row
        pattern_dict[(0, x, 0, x, x, x, 0)] = 100000 * x
        pattern_dict[(0, x, x, 0, x, x, 0)] = 100000 * x
        pattern_dict[(0, x, x, x, x, y)] = 10000 * x # Closed four-in-a-row (blocked on one end)
        pattern_dict[(y, x, x, x, x, 0)] = 10000 * x
        pattern_dict[(y, x, x, x, x, y)] = -10 * x # Fully closed four-in-a-row (blocked on both ends)
        pattern_dict[(0, x, x, x, 0)] = 1000 * x  # Open-ended three-in-a-row (potential to form four-in-a-row)
        pattern_dict[(0, x, 0, x, x, 0)] = 1000 * x
        pattern_dict[(0, x, x, 0, x, 0)] = 1000 * x
        pattern_dict[(0, 0, x, x, 0)] = 100 * x # Open-ended two-in-a-row (early game potential)
        x += 2 # Switch to the other player (1 for AI pieces)
    return pattern_dict
# Generate the global pattern dictionary
PATTERN_DICT = create_pattern_dict()

# Evaluation Function for AI : Scores the current board state for a given player
def evaluate_board(board, player):
    # Determine the opponent's piece based on the current player
    opponent = WHITE_PIECE if player == BLACK_PIECE else BLACK_PIECE
    score = 0 # Initialize the score to 0
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)] # Define directions to check: right, down, diagonal down-right, and diagonal up-right

    for y in range(BOARD_SIZE): # Iterate through each cell on the board
        for x in range(BOARD_SIZE):
            if board[y][x] == EMPTY:
                continue

            current_piece = board[y][x]
            for dx, dy in directions:
                count = 0
                for i in range(5): # Check up to 5 in a row
                    nx, ny = x + i * dx, y + i * dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        if board[ny][nx] == current_piece:
                            count += 1
                        else:
                            break
                # Scoring based on the number of consecutive pieces
                if count == 2:
                    score += 10 if current_piece == player else -10
                elif count == 3:
                    score += 50 if current_piece == player else -50
                elif count == 4:
                    score += 100 if current_piece == player else -100
                elif count == 5:
                    return 1000 if current_piece == player else -1000
    return score

# Minimax with Alpha-Beta Pruning and Time Limit
def minimax(board, depth, is_maximizing, player, alpha, beta, start_time, time_limit, last_player_move):
    if time.time() - start_time > time_limit: # Check if the time limit has been exceeded
        return 0  # Time exceeded

    winner = check_winner(board) # Check if the game has a winner
    if winner == player:
        return 1000 # Return a high score if the AI player wins
    elif winner is not None:
        return -1000 # Return a low score if the opponent wins

    if depth == 0: # Base case: If the depth limit is reached, evaluate the current board state
        return evaluate_board(board, player)

    lx, ly = last_player_move
    search_radius = 2
    best_score = -float('inf') if is_maximizing else float('inf') # Initialize the best score based on whether we are maximizing or minimizing

    for y in range(max(0, ly - search_radius), min(BOARD_SIZE, ly + search_radius + 1)):
        for x in range(max(0, lx - search_radius), min(BOARD_SIZE, lx + search_radius + 1)):
            if board[y][x] == EMPTY:
                board[y][x] = player if is_maximizing else (WHITE_PIECE if player == BLACK_PIECE else BLACK_PIECE)
                score = minimax(board, depth - 1, not is_maximizing, player, alpha, beta, start_time, time_limit, (x, y))
                board[y][x] = EMPTY

                if is_maximizing:
                    best_score = max(best_score, score)
                    alpha = max(alpha, best_score)
                else:
                    best_score = min(best_score, score)
                    beta = min(beta, best_score)

                if beta <= alpha:
                    break

    return best_score

# AI Move Function
def get_ai_move(board, player, last_player_move, time_limit=10):
    best_score = -float('inf') # Initialize the best score as negative infinity (lowest possible score)
    best_move = None # Initialize the best move as None (no move chosen yet)
    start_time = time.time()
    lx, ly = last_player_move # Get the coordinates of the last player move
    search_radius = 2 # Define the search radius around the last move
    # Prioritize moves near the last player move (White)
    for y in range(max(0, ly - search_radius), min(BOARD_SIZE, ly + search_radius + 1)):
        for x in range(max(0, lx - search_radius), min(BOARD_SIZE, lx + search_radius + 1)):
            if board[y][x] == EMPTY: # Check if the current cell is empty (a valid move)
                board[y][x] = player # Temporarily place the AI player's piece on the board at (x, y)
                score = minimax(board, 3, False, player, -float('inf'), float('inf'), start_time, time_limit, (x, y))
                # Call the minimax function to evaluate the move's score
                # Depth is set to 3, meaning the algorithm looks ahead 3 moves
                # The 'False' argument indicates it is now the minimizing player's turn
                board[y][x] = EMPTY # Remove the piece after evaluation (restore the board state)

                if score > best_score:
                    best_score = score
                    best_move = (x, y)
                # Check if the time limit has been exceeded
                if time.time() - start_time > time_limit:
                    return best_move

    return best_move

def show_menu():
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

def main(stdscr, game_mode):
    global cursor_x, cursor_y, turn # Use global variables to track cursor position and turn

    # Setup curses settings
    curses.curs_set(0)  # Hide the default cursor
    stdscr.keypad(True) # Enable special keys (like arrow keys) to be read directly
    stdscr.clear() # Clear the screen to start fresh
    stdscr.refresh() # Apply the clear to the display

    # Display initial board and instructions
    print_board(stdscr)


    while True: # Main game loop

        if game_mode == "ai" and turn == BLACK_PIECE: # Check if the current game mode is AI and if it's the Black player's turn
            if last_player_move is None:
                last_player_move = (7, 7)  # Default to center if no previous move
            ai_move = get_ai_move(board, BLACK_PIECE, last_player_move) # Get the AI's move for the Black player using the get_ai_move() function
            if ai_move: # If the AI returned a valid move (not None)
                x, y = ai_move # Unpack the move coordinates (x, y) from the AI's choice
                board[y][x] = BLACK_PIECE # Place the Black piece (AI move) on the board at the chosen coordinates
                last_player_move = (x, y)  # Update `last_player_move`
                if check_winner(board) == BLACK_PIECE: # Check if the AI's move resulted in a win for the Black player
                    print_board(stdscr) # Print the updated board to the screen
                    stdscr.addstr(BOARD_SIZE + 6, 0, "Black (AI) wins!") # Display a message indicating that the Black player (AI) has won
                    stdscr.refresh() # Refresh the screen to show the win message
                    stdscr.getch() # Wait for the user to press any key before ending the game
                    break
                turn = WHITE_PIECE # If no winner, switch the turn to the White player
                print_board(stdscr) # Print the updated board after the AI's move
                continue

        key = stdscr.getch() # Wait for user input

        # Handle quit command
        if key == ord('q'): # If 'q' is pressed, exit the loop
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

        # Initialize last player move
        last_player_move = (cursor_x, cursor_y)

        # Place a piece: 'w' for white and 'b' for black
        if key == ord('w') and turn == WHITE_PIECE: # White's turn to place a piece
            if board[cursor_y][cursor_x] == EMPTY: # Check if the selected cell is empty
                board[cursor_y][cursor_x] = WHITE_PIECE # Place the white piece
                last_player_move = (cursor_x, cursor_y)  # Update last player move
                if check_winner(board) == WHITE_PIECE: # Check if placing this piece wins the game
                    print_board(stdscr) # Update the board display
                    stdscr.addstr(BOARD_SIZE + 6, 0, "White wins!") # Display win message
                    stdscr.refresh()  # Refresh display to show changes
                    stdscr.getch() # Wait for any key to be pressed before ending
                    break # Exit the loop to end the game
                turn = BLACK_PIECE # Switch turn to black if no winner

        # PvP mode
        if key == ord('b') and turn == BLACK_PIECE:
            if board[cursor_y][cursor_x] == EMPTY:
                board[cursor_y][cursor_x] = BLACK_PIECE
                if check_winner(board) == BLACK_PIECE:
                    print_board(stdscr)
                    stdscr.addstr(BOARD_SIZE + 6, 0, "Black wins!")
                    stdscr.refresh()
                    stdscr.getch()
                    break
                turn = WHITE_PIECE

        # Refresh the board display after each action
        print_board(stdscr)

# Run the banner and curses wrapper to initiate the main loop
if __name__ == "__main__":
    print_banner()
    game_mode = show_menu()
    print(f"Selected game mode: {'Player vs Player' if game_mode == 'pvp' else 'Play with AI'}")
    curses.wrapper(main, game_mode)
