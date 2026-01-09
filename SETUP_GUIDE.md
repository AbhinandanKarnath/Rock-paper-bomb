# Rock-Paper-Scissors-Plus Setup Guide

## Current Issues

Based on the test results, you have **2 main issues**:

### 1. ❌ API Quota Exceeded (429 Error)
Your API key has exceeded its free quota.

**Solution:**
- Get a NEW API key from: https://aistudio.google.com/app/apikey
- OR wait 1 minute for quota reset

### 2. ⚠️ Package Installation
You need the correct Google Generative AI package.

## Quick Fix Steps

### Step 1: Install the correct package
```bash
pip install google-generativeai
```

### Step 2: Get a new API key
1. Go to: https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy your new key

### Step 3: Set your API key (choose one method)

**Method A - Environment Variable (Recommended):**
```bash
# Windows CMD
set GOOGLE_API_KEY=your_new_api_key_here

# Windows PowerShell
$env:GOOGLE_API_KEY="your_new_api_key_here"
```

**Method B - Update the code:**
Edit `game_referee.py` line 12:
```python
API_KEY = os.getenv("GOOGLE_API_KEY", "YOUR_NEW_KEY_HERE")
```

### Step 4: Test it
```bash
python test_api.py
```

You should see: ✅ SUCCESS!

### Step 5: Run the game
```bash
python game_referee.py
```

## Troubleshooting

### Still getting 429 error?
- Wait 60 seconds and try again
- Free tier has rate limits (15 requests per minute)

### Package not found?
```bash
pip uninstall google-genai google-generativeai
pip install google-generativeai
```

### Other errors?
- Check internet connection
- Verify API key is valid
- Try: `pip list | findstr google`

## API Key Information

**Free Tier Limits:**
- 15 requests per minute
- 1 million tokens per minute
- 1500 requests per day

**Models Available:**
- ✅ gemini-1.5-flash-latest (recommended)
- ✅ gemini-1.5-pro-latest (slower, more capable)
- ❌ gemini-2.0-flash-exp (requires paid tier)

---

**Need help?** Run `python test_api.py` and share the output!
