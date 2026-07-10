import discord
import os
import asyncio
from groq import AsyncGroq
from flask import Flask
from threading import Thread

# --- FLASK KEEP-ALIVE SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and vibing!"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.daemon = True
    t.start()

# --- DISCORD & GROQ SETUP ---
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

# Initialize the Groq client
GROQ_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ai_client = AsyncGroq(api_key=GROQ_KEY)

@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return
        
    try:
        # Hitting Groq's Llama 3.3 model for crazy fast speeds
        response = await ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a chill, helpful bot in a coding and gaming Discord server. Keep your replies extremely short, punchy, and fast. Maximum 2 sentences unless the user explicitly asks for code."},
                {"role": "user", "content": message.content}
            ],
            model="llama-3.3-70b-versatile",
        )
        
        await message.reply(response.choices[0].message.content)
        
    except Exception as e:
        print(f"API Error: {e}") 
        await message.reply(f"Bro my brain lagged. Error: `{str(e)}`")

if __name__ == "__main__":
    keep_alive()
    discord_client.run(DISCORD_TOKEN)
