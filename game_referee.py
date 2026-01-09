import os
import random
from google import genai
from google.genai import types

# --- 1. Game Logic & State (The Engine) ---
class GameEngine:
    def __init__(self):
        self.user_score = 0
        self.bot_score = 0
        self.round_count = 0
        self.max_rounds = 3
        self.user_bomb_used = False
        self.bot_bomb_used = False
        self.game_over = False

    def get_bot_move(self):
        # Bot logic: Random, with 10% chance to use bomb if available
        moves = ["rock", "paper", "scissors"]
        if not self.bot_bomb_used:
            if random.random() < 0.1: 
                return "bomb"
        return random.choice(moves)

    def resolve_round(self, user_move: str):
        """
        Validates move, plays a round, updates state, and returns result.
        Args:
            user_move: The move played by the user (rock, paper, scissors, bomb).
        """
        if self.game_over:
            return {"status": "game_over", "message": "Game is already finished."}

        user_move = user_move.lower().strip()
        valid_moves = ["rock", "paper", "scissors", "bomb"]
        
        # --- Validation Logic ---
        if user_move not in valid_moves:
            self.round_count += 1
            if self.round_count >= self.max_rounds: self.game_over = True
            return {
                "round": self.round_count,
                "status": "invalid",
                "message": f"Invalid move '{user_move}'. Round wasted.",
                "scores": f"User: {self.user_score}, Bot: {self.bot_score}",
                "game_over": self.game_over
            }

        if user_move == "bomb":
            if self.user_bomb_used:
                self.round_count += 1
                if self.round_count >= self.max_rounds: self.game_over = True
                return {
                    "round": self.round_count,
                    "status": "invalid",
                    "message": "Bomb already used! Round wasted.",
                    "scores": f"User: {self.user_score}, Bot: {self.bot_score}",
                    "game_over": self.game_over
                }
            self.user_bomb_used = True

        # --- Play Round ---
        bot_move = self.get_bot_move()
        if bot_move == "bomb": self.bot_bomb_used = True
        
        winner = "draw"
        
        if user_move == bot_move:
            winner = "draw"
        elif user_move == "bomb":
            winner = "user"
        elif bot_move == "bomb":
            winner = "bot"
        elif (user_move == "rock" and bot_move == "scissors") or \
             (user_move == "scissors" and bot_move == "paper") or \
             (user_move == "paper" and bot_move == "rock"):
            winner = "user"
        else:
            winner = "bot"

        # --- Update State ---
        self.round_count += 1
        if winner == "user": self.user_score += 1
        elif winner == "bot": self.bot_score += 1
        
        if self.round_count >= self.max_rounds:
            self.game_over = True

        final_result = None
        if self.game_over:
            if self.user_score > self.bot_score: final_result = "User Wins Game!"
            elif self.bot_score > self.user_score: final_result = "Bot Wins Game!"
            else: final_result = "Game Ends in Draw!"

        return {
            "round": self.round_count,
            "moves": f"User: {user_move} vs Bot: {bot_move}",
            "round_winner": winner,
            "scores": f"User: {self.user_score}, Bot: {self.bot_score}",
            "game_over": self.game_over,
            "final_result": final_result
        }

# --- 2. Tool Definition & Agent Configuration ---

def start_game():
    # Initialize Engine
    engine = GameEngine()
    
    # Initialize Client (New SDK)
    api_key = "AIzaSyAy_aF39dM8QwWaDc67I7ihqmpSZk-v-dI"
    client = genai.Client(api_key=api_key)

    # Define Configuration with Tools
    # In the new SDK, passing the function directly in a list works for Python automatic mapping
    game_config = types.GenerateContentConfig(
        tools=[engine.resolve_round],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
        system_instruction="""
        You are a referee for Rock-Paper-Scissors-Plus.
        1. Explain rules concisely (max 5 lines) at the start.
        2. Ask for the user's move.
        3. CALL 'resolve_round' with the user's move.
        4. State Round #, Moves, Winner, and Score based purely on tool output.
        5. If game_over is true, declare the final winner and stop.
        """
    )

    # Try different model names
    models_to_try = [
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash", 
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro-002",
        "gemini-1.5-pro-001"
    ]
    chat = None
    last_error = None
    
    print("🔄 Trying to connect to Google ADK...")
    
    for model_name in models_to_try:
        try:
            chat = client.chats.create(
                model=model_name,
                config=game_config
            )
            print(f"✓ Successfully connected using: {model_name}\n")
            break
        except Exception as e:
            err_str = str(e)
            last_error = err_str
            if "404" in err_str or "NOT_FOUND" in err_str:
                print(f"  ✗ {model_name}: Model not found")
            elif "429" in err_str or "quota" in err_str.lower():
                print(f"  ✗ {model_name}: Quota exceeded")
            else:
                print(f"  ✗ {model_name}: {err_str[:60]}")
            continue
    
    if chat is None:
        print("\n❌ Failed to connect to any model.")
        print("\nPossible solutions:")
        print("1. Your API key may have quota issues")
        print("2. Get a new key: https://aistudio.google.com/app/apikey")
        print("3. Wait 60 seconds for quota reset")
        if last_error:
            print(f"\nLast error: {last_error[:200]}")
        return

    # --- 3. The Game Loop ---
    # Initial trigger with retry
    import time
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = chat.send_message("Start the game.")
            print(f"Referee:\n{response.text}\n")
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    print(f"⏳ Rate limit hit. Waiting {wait_time} seconds before retry {attempt+2}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    print(f"\n❌ API quota exhausted after {max_retries} attempts.")
                    print("Your API key has hit its rate limit.")
                    print("\n🔧 Solutions:")
                    print("1. Wait 60 seconds and try again")
                    print("2. Get a NEW API key from: https://aistudio.google.com/app/apikey")
                    print("3. Check your usage: https://ai.dev/rate-limit")
                    return
            else:
                print(f"Error: {err_str[:150]}")
                return

    while not engine.game_over:
        user_input = input("Your Move > ")
        if not user_input: continue

        try:
            # The SDK handles the tool call loop automatically
            response = chat.send_message(user_input)
            print(f"\nReferee:\n{response.text}")
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                print(f"\n⚠️  Rate limit reached. Waiting 5 seconds...")
                time.sleep(5)
                try:
                    response = chat.send_message(user_input)
                    print(f"\nReferee:\n{response.text}")
                except:
                    print("❌ Still hitting rate limits. Please wait 60 seconds and restart the game.")
                    break
            else:
                print(f"Error: {err_str[:150]}")
                break

if __name__ == "__main__":
    start_game()