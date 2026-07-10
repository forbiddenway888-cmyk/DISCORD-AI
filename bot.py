import discord
import os
import asyncio
from groq import AsyncGroq
from flask import Flask
from threading import Thread
from discord.ext import tasks

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


# --- THE MEMORY BANK ---
# This dictionary maps user IDs to their personal chat history
chat_history = {}
MAX_HISTORY = 12 # Keeps the last 12 messages so we don't crash Groq's token limit


# --- 20-MINUTE AUTO-ANNOUNCEMENT ---
@tasks.loop(minutes=20)
async def everyone_reminder():
    # Look through all channels the bot can see
    for channel in discord_client.get_all_channels():
        # Replace "ai-chat" with the exact name of the text channel you want to target
        if channel.name == "ai-chat" and isinstance(channel, discord.TextChannel):
            try:
                await channel.send("@everyone wake up! Tag me if you want to chat or use the AI!")
                print("🔥 Sent 20-minute wake-up reminder.")
                break # Stop looking after finding the channel
            except Exception as e:
                print(f"Failed to send reminder: {e}")

@everyone_reminder.before_loop
async def before_reminder():
    # Forces the loop to wait until the bot is completely logged in before starting
    await discord_client.wait_until_ready()
    
@discord_client.event
async def on_ready():
    print(f'🔥 WE LIVE! Logged in as {discord_client.user}')
    # Start the 20-minute timer as soon as the bot boots up
    if not everyone_reminder.is_running():
        everyone_reminder.start()
# ==========================================


# --- MESSAGE HANDLING ---
@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return

    # CRITICAL: Ignore the message unless the bot is specifically tagged
    if not discord_client.user.mentioned_in(message):
        return

    user_id = message.author.id

    # 1. New user setup with the custom creator rules added into the system prompt
    if user_id not in chat_history:
        chat_history[user_id] = [
            {
                "role": "system", 
                "content": (
                    "You are a chill, highly intelligent bot in the FORBID • OPS Discord server. "
                    "You talk like a real human, keep things conversational, and remember context perfectly. "
                    "You can give detailed answers when asked, but keep the vibe relaxed. "
                    "CRITICAL RULE: If anyone asks who made you, who your owner is, or who created you, "
                    "you must state that you were made by FORB1D🔥. Do not bring this up randomly—only state "
                    "it when specifically asked about your origin, owner, or creator, keeping it natural."
                )
            }
        ]

    # 2. Add the user's new message to their history
    chat_history[user_id].append({"role": "user", "content": message.content})

    # 3. Memory Wipe Check (Sliding Window)
    if len(chat_history[user_id]) > MAX_HISTORY:
        chat_history[user_id] = [chat_history[user_id][0]] + chat_history[user_id][-(MAX_HISTORY-1):]

    try:
        # 4. Send the ENTIRE history list to Groq
        response = await ai_client.chat.completions.create(
            messages=chat_history[user_id],
            model="llama-3.3-70b-versatile",
        )
        
        bot_reply = response.choices[0].message.content
        
        # 5. Add the AI's reply to the history
        chat_history[user_id].append({"role": "assistant", "content": bot_reply})
        
        await message.reply(bot_reply)
        
    except Exception as e:
        print(f"API Error: {e}") 
        chat_history[user_id].pop() 
        await message.reply(f"Bro my brain lagged. Error: `{str(e)}`")


# Start the web server, THEN start the bot
if __name__ == "__main__":
    keep_alive()
    discord_client.run(DISCORD_TOKEN)
