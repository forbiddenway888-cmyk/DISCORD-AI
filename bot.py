import discord
import os
import asyncio
import urllib.parse
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

# You only need these two keys! No image API key needed.
GROQ_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ai_client = AsyncGroq(api_key=GROQ_KEY)

# --- THE MEMORY BANK ---
chat_history = {}
MAX_HISTORY = 12 

# --- 20-MINUTE AUTO-ANNOUNCEMENT ---
@tasks.loop(minutes=20)
async def everyone_reminder():
    for channel in discord_client.get_all_channels():
        # Make sure this matches your exact channel name
        if channel.name == "♠️︱chat︱♠️" and isinstance(channel, discord.TextChannel):
            try:
                await channel.send("@everyone wake up! Tag me to chat or ask me to create an image!")
                print("🔥 Sent 20-minute wake-up reminder.")
                break 
            except Exception as e:
                print(f"Failed to send reminder: {e}")

@everyone_reminder.before_loop
async def before_reminder():
    await discord_client.wait_until_ready()
    
@discord_client.event
async def on_ready():
    print(f'🔥 WE LIVE! Logged in as {discord_client.user}')
    if not everyone_reminder.is_running():
        everyone_reminder.start()

# --- MESSAGE HANDLING ---
# --- MESSAGE HANDLING ---
@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return

    # CRITICAL: Ignore the message unless the bot is specifically tagged
    if not discord_client.user.mentioned_in(message):
        return

    # Clean the bot's tag out of the message text
    # Clean the bot's tag out of the message text
    raw_content = message.content.replace(f'<@{discord_client.user.id}>', '').strip()
    
    # ==========================================
    # IMAGE SCANNER (Checking for uploads)
    # ==========================================
    image_url = None
    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith('image/'):
                image_url = att.url
                break

    # If there is no text AND no image uploaded, tell them to do something
    if not raw_content and not image_url:
        await message.reply("Yo, what's up? Tag me and say something, or upload an image for me to scan!")
        return

    user_id = message.author.id

    # 1. THE NEW SMART SYSTEM PROMPT
    if user_id not in chat_history:
        chat_history[user_id] = [
            {
                "role": "system", 
                "content": (
                    "You are a chill, highly intelligent bot in the FORBID • OPS Discord server. "
                    "You keep things conversational and relaxed. "
                    "CRITICAL RULE 1: If anyone asks who made you, state you were made by FORB1D🔥. "
                    "CRITICAL RULE 2: You have an image generator. If the user asks for a picture, drawing, photo, or visual representation of ANYTHING, "
                    "you MUST reply starting with exactly the word [DRAW] followed by a highly detailed prompt describing what they want. "
                    "Do not add any other conversational text. Just the [DRAW] tag and the prompt. "
                    "Example: [DRAW] A realistic cyberpunk city with neon lights. "
                    "If they just want to chat normally, reply with normal text and no tags."
                )
            }
        ]

    # If they sent an image but didn't type a message, give the AI a default prompt
    user_text = raw_content if raw_content else "Describe what is in this image for me bro."

    # 2. Add the user's TEXT to history (We only save text to memory so it doesn't break future chat)
    chat_history[user_id].append({"role": "user", "content": user_text})

    # 3. Memory Wipe Check
    if len(chat_history[user_id]) > MAX_HISTORY:
        chat_history[user_id] = [chat_history[user_id][0]] + chat_history[user_id][-(MAX_HISTORY-1):]

    try:
        # Create a temporary list of messages to send to the API
        api_messages = list(chat_history[user_id])
        current_model = "meta-llama/llama-4-scout-17b-16e-instruct"

        # If an image was uploaded, switch the brain to the Vision model!
        if image_url:
            # Modify the very last message in our temporary list so it includes the image file
            api_messages[-1] = {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
            current_model = "llama-3.2-90b-vision-preview"

        # 4. Send the message to Groq using whichever model it auto-selected
        response = await ai_client.chat.completions.create(
            messages=api_messages,
            model=current_model,
        )
        
        bot_reply = response.choices[0].message.content
        
        # ==========================================
        # THE AI ROUTER (INTERCEPTING THE IMAGE)
        # ==========================================
        # ==========================================
        # THE AI ROUTER (INTERCEPTING THE IMAGE)
        # ==========================================
        if bot_reply.startswith("[DRAW]"):
            # Groq decided to draw! Isolate the prompt text
            image_prompt = bot_reply.replace("[DRAW]", "").strip()
            
            async with message.channel.typing():
                # Hit the free image API
                safe_prompt = urllib.parse.quote(image_prompt)
                image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}"
                
                # DISCORD SAFETY CHECK: Titles can only be 256 characters max.
                # If the prompt is massive, we chop it and add "..." at the end
                display_title = f"🎨 {image_prompt}"
                if len(display_title) > 256:
                    display_title = display_title[:253] + "..."
                
                # Embed the image using our safe, shortened title
                embed = discord.Embed(title=display_title, color=discord.Color.purple())
                embed.set_image(url=image_url)
                embed.set_footer(text="Generated by FORB1D🔥 via FORBID API")
                
                await message.reply(embed=embed)
        else:
            # Groq decided to chat normally, just send the text
            await message.reply(bot_reply)

        # 5. Add Groq's reply to the history so it remembers what it did
        chat_history[user_id].append({"role": "assistant", "content": bot_reply})
        
    except Exception as e:
        print(f"API Error: {e}") 
        chat_history[user_id].pop() 
        await message.reply(f"Bro my brain lagged. Error: `{str(e)}`")

# Start the bot
if __name__ == "__main__":
    keep_alive()
    discord_client.run(DISCORD_TOKEN)
