import time
from Gomoku2 import check_winner, get_ai_move, BOARD_SIZE, EMPTY, WHITE_PIECE, BLACK_PIECE

def initialize_board():
    return [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

def random_move(board):
    from random import choice
    empty_positions = [(x, y) for x in range(BOARD_SIZE) for y in range(BOARD_SIZE) if board[y][x] == EMPTY]
    return choice(empty_positions) if empty_positions else None

def print_board(board):
    """Print the current game board."""
    for row in board:
        print(' '.join(row))
    print("\n" + "-" * (BOARD_SIZE * 2))

def simulate_game(game_num, results):
    print(f"Starting Game {game_num + 1}")
    board = initialize_board()
    last_move = (BOARD_SIZE // 2, BOARD_SIZE // 2)  # Start near the center
    board[last_move[1]][last_move[0]] = WHITE_PIECE  # First move by player
    turn = BLACK_PIECE  # AI starts

    print("Initial Board:")
    print_board(board)
    time.sleep(1)  # Pause for visualization

    start_time = time.time()  # Track game start time
    ai_moves = 0  # Count AI's moves
    total_ai_time = 0  # Track total time AI spends on moves

    while True:
        if turn == BLACK_PIECE:
            print("AI's Turn:")
            move_start_time = time.time()  # Start timing AI's move
            ai_move = get_ai_move(board, BLACK_PIECE, last_move)
            move_duration = time.time() - move_start_time  # Time for this move
            total_ai_time += move_duration
            ai_moves += 1

            if not ai_move:
                print("AI cannot make a move. Game ends in a draw.")
                results["Draws"] += 1
                break

            x, y = ai_move
            board[y][x] = BLACK_PIECE
            last_move = ai_move

            if check_winner(board) == BLACK_PIECE:
                print_board(board)
                print("AI Wins!")
                results["AI Wins"] += 1
                break
        else:
            print("Random Player's Turn:")
            player_move = random_move(board)
            if not player_move:
                print("No moves left for the random player. Game ends in a draw.")
                results["Draws"] += 1
                break

            x, y = player_move
            board[y][x] = WHITE_PIECE
            last_move = player_move

            if check_winner(board) == WHITE_PIECE:
                print_board(board)
                print("Random Player Wins!")
                results["Player Wins"] += 1
                break

        print_board(board)  # Show the updated board
        time.sleep(1)  # Add delay for visualization
        turn = WHITE_PIECE if turn == BLACK_PIECE else BLACK_PIECE  # Switch turn

    game_duration = time.time() - start_time
    print(f"Game Over in {game_duration:.2f} seconds\n")
    results["Game Durations"].append(game_duration)
    results["Total AI Moves"] += ai_moves
    results["Total AI Time"] += total_ai_time

def main():
    try:
        num_games = int(input("Enter the number of games to run: "))
    except ValueError:
        print("Invalid input. Defaulting to 1 game.")
        num_games = 1

    # Initialize results dictionary
    results = {
        "AI Wins": 0,
        "Player Wins": 0,
        "Draws": 0,
        "Game Durations": [],
        "Total AI Moves": 0,
        "Total AI Time": 0,
    }

    for game_num in range(num_games):
        simulate_game(game_num, results)

    # Calculate metrics
    total_games = results["AI Wins"] + results["Player Wins"] + results["Draws"]
    avg_time_per_move = results["Total AI Time"] / results["Total AI Moves"] if results["Total AI Moves"] > 0 else 0
    avg_game_duration = sum(results["Game Durations"]) / total_games if total_games > 0 else 0

    # Display results
    print("\nPerformance Metrics:")
    print(f"Number of Games Run: {total_games}")
    print(f"AI Win Rate: {results['AI Wins'] / total_games * 100:.2f}%")
    print(f"Player Win Rate: {results['Player Wins'] / total_games * 100:.2f}%")
    print(f"Draw Rate: {results['Draws'] / total_games * 100:.2f}%")
    print(f"Average Time Per AI Move: {avg_time_per_move:.2f} seconds")
    print(f"Average Game Duration: {avg_game_duration:.2f} seconds")
    print(f"Total AI Moves: {results['Total AI Moves']}")

if __name__ == "__main__":
    main()
