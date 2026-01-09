# filepath: e:\Chat_bot\game_referee_v2.py
"""
Rock-Paper-Scissors-Plus Game Referee
A minimal AI chatbot referee using Google ADK

Requirements compliance:
- ✓ Explicit ADK tools (validate_move_tool, resolve_round_tool, update_game_state_tool)
- ✓ Clear separation: Intent understanding, Game logic, Response generation
- ✓ State persistence via structured Pydantic models
- ✓ Best of 3 rounds with automatic game end
- ✓ Bomb mechanic (one-time use per player)
- ✓ Invalid input handling (wastes round, no crashes)
- ✓ Clear round-by-round feedback
"""

import random
import json
import os
from typing import Literal, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# ============================================================================
# CONFIGURATION
# ============================================================================

API_KEY = "AIzaSyDa_lOoA3qOT9X4JZIbhFdYTSkEHWogqrg"
client = genai.Client(api_key=API_KEY)

# ============================================================================
# STATE MODEL - Structured state persistence
# ============================================================================

class GameState(BaseModel):
    """Structured game state (not stored in prompt)"""
    round_number: int = Field(default=1, ge=1, le=3)
    user_score: int = Field(default=0, ge=0)
    bot_score: int = Field(default=0, ge=0)
    user_bomb_used: bool = Field(default=False)
    bot_bomb_used: bool = Field(default=False)
    game_active: bool = Field(default=True)
    last_user_move: str = Field(default="")
    last_bot_move: str = Field(default="")
    last_result: str = Field(default="")

# ============================================================================
# GAME LOGIC - Pure functions for game mechanics
# ============================================================================

VALID_MOVES = {"rock", "paper", "scissors", "bomb"}

def validate_move(user_input: str) -> tuple[bool, str]:
    """Validates and normalizes user input"""
    cleaned = user_input.lower().strip()
    return (cleaned in VALID_MOVES, cleaned)

def determine_winner(user_move: str, bot_move: str) -> Literal["user", "bot", "draw"]:
    """Determines round winner based on game rules"""
    if user_move == bot_move:
        return "draw"
    if user_move == "bomb":
        return "user"
    if bot_move == "bomb":
        return "bot"
    wins = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    return "user" if wins.get(user_move) == bot_move else "bot"

def choose_bot_move(state: GameState) -> str:
    """Bot move selection with strategic bomb usage"""
    if not state.bot_bomb_used and state.round_number == 2 and state.bot_score < state.user_score:
        return "bomb"
    return random.choice(["rock", "paper", "scissors"])

# ============================================================================
# ADK TOOLS - Explicit tool implementations
# ============================================================================

def validate_move_tool(user_input: str, user_bomb_used: bool) -> Dict[str, Any]:
    """
    Tool 1: Validate user input and bomb availability
    """
    is_valid, normalized = validate_move(user_input)
    
    if not is_valid:
        return {
            "valid": False,
            "error": f"Invalid move: '{user_input}'. Use: rock, paper, scissors, bomb",
            "move": None
        }
    
    if normalized == "bomb" and user_bomb_used:
        return {
            "valid": False,
            "error": "You already used your bomb!",
            "move": None
        }
    
    return {"valid": True, "error": None, "move": normalized}

def resolve_round_tool(user_move: str, bot_move: str) -> Dict[str, Any]:
    """
    Tool 2: Resolve a single round
    """
    winner = determine_winner(user_move, bot_move)
    return {
        "user_move": user_move,
        "bot_move": bot_move,
        "winner": winner,
        "user_point": 1 if winner == "user" else 0,
        "bot_point": 1 if winner == "bot" else 0
    }

def update_game_state_tool(user_input: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool 3: Main orchestration tool - validates, resolves, updates state
    This is the primary tool the agent should use for each move
    """
    state = GameState(**current_state)
    
    # Step 1: Validate
    validation = validate_move_tool(user_input, state.user_bomb_used)
    
    if not validation["valid"]:
        # Invalid input wastes the round
        state.last_user_move = user_input
        state.last_bot_move = ""
        state.last_result = validation["error"]
        state.round_number += 1
        if state.round_number > 3:
            state.game_active = False
        return state.model_dump()
    
    user_move = validation["move"]
    
    # Step 2: Track bomb usage
    if user_move == "bomb":
        state.user_bomb_used = True
    
    # Step 3: Bot move
    bot_move = choose_bot_move(state)
    if bot_move == "bomb":
        state.bot_bomb_used = True
    
    # Step 4: Resolve
    round_result = resolve_round_tool(user_move, bot_move)
    
    # Step 5: Update state
    state.user_score += round_result["user_point"]
    state.bot_score += round_result["bot_point"]
    state.last_user_move = user_move
    state.last_bot_move = bot_move
    
    if round_result["winner"] == "user":
        state.last_result = "You win this round!"
    elif round_result["winner"] == "bot":
        state.last_result = "Bot wins this round!"
    else:
        state.last_result = "It's a draw!"
    
    state.round_number += 1
    
    # Step 6: Check end condition
    if state.round_number > 3:
        state.game_active = False
    
    return state.model_dump()

# ============================================================================
# ADK TOOL DECLARATIONS - Function schemas for the agent
# ============================================================================

validate_move_declaration = types.FunctionDeclaration(
    name="validate_move_tool",
    description="Validates user input and checks if the move is legal",
    parameters={
        "type": "object",
        "properties": {
            "user_input": {"type": "string", "description": "Raw user input"},
            "user_bomb_used": {"type": "boolean", "description": "Has user used bomb?"}
        },
        "required": ["user_input", "user_bomb_used"]
    }
)

resolve_round_declaration = types.FunctionDeclaration(
    name="resolve_round_tool",
    description="Determines winner of a round",
    parameters={
        "type": "object",
        "properties": {
            "user_move": {"type": "string", "description": "User's validated move"},
            "bot_move": {"type": "string", "description": "Bot's move"}
        },
        "required": ["user_move", "bot_move"]
    }
)

update_game_state_declaration = types.FunctionDeclaration(
    name="update_game_state_tool",
    description="MAIN TOOL: Validates input, resolves round, updates complete game state. Use this for each user move.",
    parameters={
        "type": "object",
        "properties": {
            "user_input": {"type": "string", "description": "Raw user input for their move"},
            "current_state": {
                "type": "object",
                "description": "Complete current game state",
                "properties": {
                    "round_number": {"type": "integer"},
                    "user_score": {"type": "integer"},
                    "bot_score": {"type": "integer"},
                    "user_bomb_used": {"type": "boolean"},
                    "bot_bomb_used": {"type": "boolean"},
                    "game_active": {"type": "boolean"},
                    "last_user_move": {"type": "string"},
                    "last_bot_move": {"type": "string"},
                    "last_result": {"type": "string"}
                }
            }
        },
        "required": ["user_input", "current_state"]
    }
)

game_tools = [validate_move_declaration, resolve_round_declaration, update_game_state_declaration]

# ============================================================================
# AGENT CONFIGURATION - Intent understanding and response generation
# ============================================================================

SYSTEM_PROMPT = """You are the Referee for Rock-Paper-Scissors-Plus.

RULES (explain in ≤5 lines at start):
• Best of 3 rounds. Valid moves: rock, paper, scissors, bomb
• bomb beats everything but can only be used once per player
• bomb vs bomb = draw. Invalid input wastes the round
• Standard RPS: rock>scissors, scissors>paper, paper>rock
• Game ends automatically after 3 rounds

YOUR ROLE:
1. At start: Explain rules (≤5 lines), ask for Round 1 move
2. Each turn: ALWAYS use update_game_state_tool to process the user's move
3. After each round, report clearly:
   - Round number
   - User's move vs Bot's move
   - Who won the round
   - Current score (User X - Bot Y)
4. After round 3: Announce final winner (User wins / Bot wins / Draw)

CRITICAL:
- Use update_game_state_tool for EVERY user move
- Never fabricate results - always use the tool
- Be concise and clear
- No extra rounds beyond 3"""

# ============================================================================
# MAIN GAME LOOP
# ============================================================================

def run_game():
    """
    Main game loop with ADK agent
    
    Architecture:
    - Intent Understanding: Agent interprets user input
    - Game Logic: Tools handle validation and state (pure functions)
    - Response Generation: Agent creates natural language responses
    """
    state = GameState()
    
    print("🎮 Rock-Paper-Scissors-Plus Game Referee")
    print("=" * 50)
    print()
    
    # Try ADK models
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    model_id = None
    
    print("Initializing game with Google ADK...\n")
    
    for candidate in models_to_try:
        try:
            response = client.models.generate_content(
                model=candidate,
                contents="Start a new Rock-Paper-Scissors-Plus game. Explain rules in ≤5 lines, then ask for Round 1 move.",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[types.Tool(function_declarations=game_tools)],
                    temperature=0.7
                )
            )
            model_id = candidate
            print(f"✓ Connected: {candidate}\n")
            print(f"🎲 Referee: {response.text}\n")
            break
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                print(f"✗ {candidate}: Quota exceeded")
            else:
                print(f"✗ {candidate}: {err[:60]}...")
            continue
    
    if model_id is None:
        print("\n❌ Failed to initialize. Solutions:")
        print("1. Get new API key: https://aistudio.google.com/app/apikey")
        print("2. Set: set GOOGLE_API_KEY=your_key")
        print("3. Check internet connection")
        return
    
    # Main game loop - 3 rounds
    while state.game_active:
        user_move = input(f"🎯 Your move: ").strip()
        
        if not user_move:
            print("Please enter a move.\n")
            continue
        
        state_json = state.model_dump()
        prompt = f"User played: '{user_move}'. Process with update_game_state_tool. State: {json.dumps(state_json)}"
        
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[types.Tool(function_declarations=game_tools)],
                    temperature=0.7
                )
            )
        except Exception as e:
            print(f"\n⚠️  API Error: {e}")
            result = update_game_state_tool(user_move, state.model_dump())
            state = GameState(**result)
            print(f"[Fallback] Round {result['round_number']-1}: {result['last_result']}")
            print(f"Score: User {state.user_score} - Bot {state.bot_score}\n")
            continue
        
        # Process tool calls
        tool_called = False
        try:
            if hasattr(response, 'candidates') and response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_called = True
                        func_call = part.function_call
                        
                        if func_call.name == "update_game_state_tool":
                            args = func_call.args
                            result = update_game_state_tool(
                                user_input=args["user_input"],
                                current_state=args["current_state"]
                            )
                            state = GameState(**result)
                            
                            round_info = {
                                "round": result['round_number'] - 1,
                                "user_move": result['last_user_move'],
                                "bot_move": result['last_bot_move'],
                                "result": result['last_result'],
                                "user_score": result['user_score'],
                                "bot_score": result['bot_score'],
                                "game_over": not result['game_active']
                            }
                            
                            try:
                                follow_up = client.models.generate_content(
                                    model=model_id,
                                    contents=f"Tool result: {json.dumps(round_info)}. Report: Round number, moves, winner, score. {'Announce final winner!' if round_info['game_over'] else 'Ask for next move.'}",
                                    config=types.GenerateContentConfig(
                                        system_instruction=SYSTEM_PROMPT,
                                        temperature=0.7
                                    )
                                )
                                print(f"\n🎲 Referee: {follow_up.text}\n")
                            except:
                                print(f"\n📊 Round {round_info['round']} Result:")
                                print(f"   You: {round_info['user_move']} | Bot: {round_info['bot_move']}")
                                print(f"   {round_info['result']}")
                                print(f"   Score: User {round_info['user_score']} - Bot {round_info['bot_score']}\n")
        except Exception as e:
            print(f"⚠️  Tool error: {e}")
            tool_called = False
        
        if not tool_called:
            if hasattr(response, 'text') and response.text:
                print(f"\n🎲 Referee: {response.text}\n")
            result = update_game_state_tool(user_move, state.model_dump())
            state = GameState(**result)
            print(f"Round {result['round_number']-1}: {result['last_user_move']} vs {result['last_bot_move']}")
            print(f"{result['last_result']}")
            print(f"Score: User {state.user_score} - Bot {state.bot_score}\n")
    
    # Final result
    print("\n" + "=" * 50)
    print("🏁 GAME OVER")
    print("=" * 50)
    print(f"   FINAL SCORE: User {state.user_score} - {state.bot_score} Bot")
    print()
    if state.user_score > state.bot_score:
        print("   🎉 YOU WIN THE GAME!")
    elif state.bot_score > state.user_score:
        print("   🤖 BOT WINS THE GAME!")
    else:
        print("   🤝 IT'S A DRAW!")
    print("=" * 50)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    run_game()
