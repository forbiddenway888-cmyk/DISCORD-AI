import discord
import os
from google import genai
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
async def on_ready():
    print(f'🔥 WE LIVE! Logged in as {discord_client.user}')

@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return
        
    try:
            async with message.channel.typing():
                # Added 'await' and '.aio' right here to stop the bot from freezing
                response = await ai_client.aio.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=message.content,
                )
            await message.reply(response.text)
    except Exception as e:
        print(f"API Error: {e}")
        await message.reply("Bro my API just choked, give me a sec.")

# Start the web server, THEN start the bot
if __name__ == "__main__":
    keep_alive()
    discord_client.run(DISCORD_TOKEN)
