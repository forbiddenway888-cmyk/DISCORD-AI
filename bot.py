import discord
import os
import asyncio
from google import genai
from google.genai import types
from flask import Flask
from threading import Thread


# --- FLASK KEEP-ALIVE SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and vibing!"

def run_server():
    # Render dynamic port assignment
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    # Push the web server to a background thread
    t = Thread(target=run_server)
    t.daemon = True
    t.start()

# --- DISCORD & GEMINI SETUP ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

ai_client = genai.Client(api_key=GEMINI_KEY)

@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return
        
    try:
        # The bot will try up to 3 times before actually failing
        for attempt in range(3):
            try:
                response = await ai_client.aio.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=message.content,
                    config=types.GenerateContentConfig(
                        max_output_tokens=150,
                        system_instruction="You are a chill, helpful bot in a coding and gaming Discord server. Keep your replies extremely short, punchy, and fast. Maximum 2 sentences unless the user explicitly asks for code."
                    )
                )
                await message.reply(response.text)
                break # Success! Break out of the loop so it doesn't repeat.
            
            except Exception as inner_error:
                # If it's a 503 overload and we have attempts left, wait 2 seconds
                if "503" in str(inner_error) and attempt < 2:
                    await asyncio.sleep(2)
                else:
                    # If it's a different error or we are out of tries, throw it to the main exception
                    raise inner_error
                    
    except Exception as e:
        # It actually failed 3 times in a row
        await message.reply(f"Bro Google's servers are completely fried right now. I'll be back in a bit.")
        print(f"Final API Error: {e}")

# Start the web server, THEN start the bot
if __name__ == "__main__":
    keep_alive()
    discord_client.run(DISCORD_TOKEN)
