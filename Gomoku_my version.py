import curses
import time  # Import time module for delay
import sys
import random

if sys.platform == "win32":
    import windows_curses  # Enables curses support on Windows

# Define board size and initial settings
BOARD_SIZE = 15
WHITE_PIECE = 'W'
BLACK_PIECE = 'B'
EMPTY = '.'

# Initialize an empty game board
board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
cursor_x, cursor_y = 7, 7 # start in the middle
turn = WHITE_PIECE  # White player starts

# Initialize AI variables, after version 0.06
# pattern_dict = create_pattern_dict()
# zobrist_table = init_zobrist()
# rolling_hash = 0
# transposition_table = {}

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
                                Version: 0.05

Author: 
Leung Wang Chan(lchan2021@csu.fullerton.edu)

"""
    print(banner)


def print_board(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "Gomoku V0.05")
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
    pattern_dict = {}
    x = -1
    while x < 2:
        y = -x
        pattern_dict[(x, x, x, x, x)] = 1000000 * x
        pattern_dict[(0, x, x, x, x, 0)] = 100000 * x
        pattern_dict[(0, x, x, x, 0, x, 0)] = 100000 * x
        pattern_dict[(0, x, 0, x, x, x, 0)] = 100000 * x
        pattern_dict[(0, x, x, 0, x, x, 0)] = 100000 * x
        pattern_dict[(0, x, x, x, x, y)] = 10000 * x
        pattern_dict[(y, x, x, x, x, 0)] = 10000 * x
        pattern_dict[(y, x, x, x, x, y)] = -10 * x
        pattern_dict[(0, x, x, x, 0)] = 1000 * x
        pattern_dict[(0, x, 0, x, x, 0)] = 1000 * x
        pattern_dict[(0, x, x, 0, x, 0)] = 1000 * x
        pattern_dict[(0, 0, x, x, 0)] = 100 * x
        x += 2
    return pattern_dict

PATTERN_DICT = create_pattern_dict()

# Evaluation Function
def evaluate_board(board, player):
    opponent = WHITE_PIECE if player == BLACK_PIECE else BLACK_PIECE
    score = 0
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] == EMPTY:
                continue

            current_piece = board[y][x]
            for dx, dy in directions:
                count = 0
                for i in range(5):
                    nx, ny = x + i * dx, y + i * dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        if board[ny][nx] == current_piece:
                            count += 1
                        else:
                            break

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
    if time.time() - start_time > time_limit:
        return 0  # Time exceeded

    winner = check_winner(board)
    if winner == player:
        return 1000
    elif winner is not None:
        return -1000

    if depth == 0:
        return evaluate_board(board, player)

    lx, ly = last_player_move
    search_radius = 2
    best_score = -float('inf') if is_maximizing else float('inf')

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
    best_score = -float('inf')
    best_move = None
    start_time = time.time()
    lx, ly = last_player_move
    search_radius = 2

    for y in range(max(0, ly - search_radius), min(BOARD_SIZE, ly + search_radius + 1)):
        for x in range(max(0, lx - search_radius), min(BOARD_SIZE, lx + search_radius + 1)):
            if board[y][x] == EMPTY:
                board[y][x] = player
                score = minimax(board, 3, False, player, -float('inf'), float('inf'), start_time, time_limit, (x, y))
                board[y][x] = EMPTY

                if score > best_score:
                    best_score = score
                    best_move = (x, y)

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

    last_player_move = (7, 7)  # Initialize `last_player_move` in the center of the board


    while True: # Main game loop

        if game_mode == "ai" and turn == BLACK_PIECE: # Check if the current game mode is AI and if it's the Black player's turn
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
