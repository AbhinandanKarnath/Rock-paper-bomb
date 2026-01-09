"""
Rock-Paper-Scissors-Plus Game Referee
Standalone version without API calls for testing
"""

import random
from typing import Literal
from pydantic import BaseModel, Field

# ============================================================================
# STATE MODEL
# ============================================================================

class GameState(BaseModel):
    """Tracks the complete game state across rounds"""
    round_number: int = Field(default=1, ge=1, le=4)  # Allow 4 to track "after round 3"
    user_score: int = Field(default=0, ge=0)
    bot_score: int = Field(default=0, ge=0)
    user_bomb_used: bool = Field(default=False)
    bot_bomb_used: bool = Field(default=False)
    game_active: bool = Field(default=True)
    last_user_move: str = Field(default="")
    last_bot_move: str = Field(default="")
    last_result: str = Field(default="")


# ============================================================================
# GAME LOGIC
# ============================================================================

VALID_MOVES = {"rock", "paper", "scissors", "bomb"}

def normalize_move(user_input: str) -> str:
    """Normalize user input to valid move or empty string"""
    cleaned = user_input.lower().strip()
    if cleaned in VALID_MOVES:
        return cleaned
    return ""


def determine_winner(user_move: str, bot_move: str) -> Literal["user", "bot", "draw"]:
    """Determine round winner based on game rules"""
    if user_move == bot_move:
        return "draw"
    
    # Bomb logic
    if user_move == "bomb":
        return "user"
    if bot_move == "bomb":
        return "bot"
    
    # Standard RPS logic
    wins = {
        "rock": "scissors",
        "scissors": "paper",
        "paper": "rock"
    }
    
    if wins.get(user_move) == bot_move:
        return "user"
    else:
        return "bot"


def choose_bot_move(state: GameState) -> str:
    """Bot move selection logic"""
    available_moves = ["rock", "paper", "scissors"]
    
    # Bot uses bomb strategically (e.g., on round 2 if losing)
    if not state.bot_bomb_used and state.round_number == 2 and state.bot_score < state.user_score:
        return "bomb"
    
    return random.choice(available_moves)


# ============================================================================
# TOOL: UPDATE GAME STATE
# ============================================================================

def update_game_state(user_input: str, current_state: dict) -> dict:
    """
    Tool: Validates user move, resolves round, and updates game state.
    
    Args:
        user_input: Raw user input string
        current_state: Current game state as dict
        
    Returns:
        Updated game state with round results
    """
    state = GameState(**current_state)
    
    # Validate user move
    user_move = normalize_move(user_input)
    
    # Handle invalid input
    if not user_move:
        state.round_number += 1
        state.last_user_move = user_input
        state.last_bot_move = ""
        state.last_result = "Invalid move! Round wasted."
        
        if state.round_number > 3:
            state.game_active = False
        
        return state.model_dump()
    
    # Check bomb usage
    if user_move == "bomb":
        if state.user_bomb_used:
            state.round_number += 1
            state.last_user_move = user_move
            state.last_bot_move = ""
            state.last_result = "You already used your bomb! Round wasted."
            
            if state.round_number > 3:
                state.game_active = False
            
            return state.model_dump()
        state.user_bomb_used = True
    
    # Bot makes move
    bot_move = choose_bot_move(state)
    if bot_move == "bomb":
        state.bot_bomb_used = True
    
    # Determine winner
    winner = determine_winner(user_move, bot_move)
    
    # Update scores
    if winner == "user":
        state.user_score += 1
        result = "You win this round!"
    elif winner == "bot":
        state.bot_score += 1
        result = "Bot wins this round!"
    else:
        result = "It's a draw!"
    
    # Update state
    state.last_user_move = user_move
    state.last_bot_move = bot_move
    state.last_result = result
    state.round_number += 1
    
    # Check if game should end
    if state.round_number > 3:
        state.game_active = False
    
    return state.model_dump()


# ============================================================================
# REFEREE (Replaces AI Agent)
# ============================================================================

def referee_explain_rules():
    """Explain game rules"""
    print("=" * 50)
    print("ROCK-PAPER-SCISSORS-PLUS RULES:")
    print("• Best of 3 rounds")
    print("• Moves: rock, paper, scissors, bomb")
    print("• bomb beats all (one-time use)")
    print("• Invalid input wastes the round")
    print("=" * 50)


def referee_announce_round(state: GameState):
    """Announce round results"""
    round_num = state.round_number - 1
    
    print(f"\n{'='*50}")
    print(f"ROUND {round_num} RESULTS")
    print(f"{'='*50}")
    
    if state.last_user_move and state.last_bot_move:
        print(f"You played: {state.last_user_move.upper()}")
        print(f"Bot played: {state.last_bot_move.upper()}")
        print(f"\n{state.last_result}")
    else:
        print(f"{state.last_result}")
    
    print(f"\nCurrent Score:")
    print(f"  You: {state.user_score}")
    print(f"  Bot: {state.bot_score}")
    print(f"{'='*50}\n")


def referee_final_result(state: GameState):
    """Announce final game result"""
    print("\n" + "=" * 50)
    print("GAME OVER!")
    print("=" * 50)
    print(f"FINAL SCORE: You {state.user_score} - {state.bot_score} Bot")
    print()
    
    if state.user_score > state.bot_score:
        print("🎉 YOU WIN THE GAME!")
    elif state.bot_score > state.user_score:
        print("🤖 BOT WINS THE GAME!")
    else:
        print("🤝 IT'S A DRAW!")
    
    print("=" * 50)


# ============================================================================
# GAME LOOP
# ============================================================================

def run_game():
    """Main game loop"""
    print("\n🎮 Rock-Paper-Scissors-Plus Game Referee\n")
    
    # Initialize game state
    state = GameState()
    
    # Explain rules
    referee_explain_rules()
    
    # Game loop - 3 rounds
    while state.game_active:
        current_round = state.round_number
        print(f"\n>>> ROUND {current_round} <<<")
        
        # Show bomb status
        if state.user_bomb_used:
            print("⚠️  Your bomb: USED")
        else:
            print("💣 Your bomb: AVAILABLE")
        
        # Get user input
        user_move = input("\nYour move (rock/paper/scissors/bomb): ").strip()
        
        # Process move using the tool
        result = update_game_state(user_move, state.model_dump())
        state = GameState(**result)
        
        # Announce results
        referee_announce_round(state)
    
    # Final result
    referee_final_result(state)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    run_game()