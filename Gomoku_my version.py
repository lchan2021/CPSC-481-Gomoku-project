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

def print_banner():
    banner = r"""
  ________                       __          
 /  _____/  ____   _____   ____ |  | ____ __ 
/   \  ___ /  _ \ /     \ /  _ \|  |/ /  |  \
\    \_\  (  <_> )  Y Y  (  <_> )    <|  |  /
 \______  /\____/|__|_|  /\____/|__|_ \____/ 
        \/             \/            \/      
                                Version: 0.04

Author: 
Leung Wang Chan(lchan2021@csu.fullerton.edu)
Tung Le        (giatung2002@csu.fullerton.edu)
Kyle Ho        (kyleho@csu.fullerton.edu)

"""
    print(banner)


def print_board(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "Gomoku V0.04")
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

def check_winner():
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


# Evaluation function for AI
def evaluate_board(board, player):
    opponent = WHITE_PIECE if player == BLACK_PIECE else BLACK_PIECE
    score = 0
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] == player:
                score += 1
            elif board[y][x] == opponent:
                score -= 1

    return score

# Minimax function with depth limit
def minimax(board, depth, is_maximizing, player):
    winner = check_winner()
    if winner == player:
        return 100
    elif winner is not None:
        return -100

    if depth == 0:
        return evaluate_board(board, player)

    best_score = -float('inf') if is_maximizing else float('inf')

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] == EMPTY:
                board[y][x] = player if is_maximizing else (WHITE_PIECE if player == BLACK_PIECE else BLACK_PIECE)
                score = minimax(board, depth - 1, not is_maximizing, player)
                board[y][x] = EMPTY

                if is_maximizing:
                    best_score = max(best_score, score)
                else:
                    best_score = min(best_score, score)

    return best_score

# AI move function
def get_ai_move(board, player):
    best_score = -float('inf')
    best_move = None

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] == EMPTY:
                board[y][x] = player
                score = minimax(board, 3, False, player)
                board[y][x] = EMPTY

                if score > best_score:
                    best_score = score
                    best_move = (x, y)

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

        if game_mode == "ai" and turn == BLACK_PIECE:
            ai_move = get_ai_move(board, BLACK_PIECE)
            if ai_move:
                x, y = ai_move
                board[y][x] = BLACK_PIECE
                if check_winner() == BLACK_PIECE:
                    print_board(stdscr)
                    stdscr.addstr(BOARD_SIZE + 6, 0, "Black (AI) wins!")
                    stdscr.refresh()
                    stdscr.getch()
                    break
                turn = WHITE_PIECE
                print_board(stdscr)
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

        # Place a piece: 'w' for white and 'b' for black
        elif key == ord('w') and turn == WHITE_PIECE: # White's turn to place a piece
            if board[cursor_y][cursor_x] == EMPTY: # Check if the selected cell is empty
                board[cursor_y][cursor_x] = WHITE_PIECE # Place the white piece
                if check_winner() == WHITE_PIECE: # Check if placing this piece wins the game
                    print_board(stdscr) # Update the board display
                    stdscr.addstr(BOARD_SIZE + 6, 0, "White wins!") # Display win message
                    stdscr.refresh()  # Refresh display to show changes
                    stdscr.getch() # Wait for any key to be pressed before ending
                    break # Exit the loop to end the game
                turn = BLACK_PIECE # Switch turn to black if no winner

        elif key == ord('b') and turn == BLACK_PIECE:
            if board[cursor_y][cursor_x] == EMPTY:
                board[cursor_y][cursor_x] = BLACK_PIECE
                if check_winner() == BLACK_PIECE:
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
