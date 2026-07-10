import discord
import os
import asyncio
import urllib.parse
from groq import AsyncGroq
from flask import Flask
from threading import Thread
from discord.ext import tasks
import aiohttp # Make sure this is at the very top!

# ==========================================
# FREE OCR IMAGE SCANNER
# ==========================================
async def scan_image_text(image_url):
    api_url = "https://api.ocr.space/parse/imageurl"
    params = {
        "apikey": "helloworld",  # Free public test key
        "url": image_url,
        "language": "eng"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as resp:
                data = await resp.json()
                if not data.get("IsErroredOnProcessing") and data.get("ParsedResults"):
                    return data["ParsedResults"][0]["ParsedText"].strip()
    except Exception as e:
        print(f"OCR Error: {e}")
    return ""

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

    # If there is no text AND no image uploaded
    if not raw_content and not image_url:
        await message.reply("Yo, what's up? Tag me and say something, or upload a screenshot for me to read!")
        return

    # If they uploaded an image, run the OCR scanner
    if image_url:
        await message.add_reaction("👁️") # Reacts so you know it's reading the image
        extracted_text = await scan_image_text(image_url)
        
        if extracted_text:
            # Secretly inject the scanned text into the prompt so Groq knows what it says
            raw_content += f"\n\n[SYSTEM NOTE: The user uploaded an image. The OCR scanner found this text inside it: '{extracted_text}']"
        else:
            raw_content += f"\n\n[SYSTEM NOTE: The user uploaded an image, but the OCR scanner couldn't find any readable words in it.]"

    user_id = message.author.id

    # 1. THE NEW SMART SYSTEM PROMPT
    # 1. THE NEW SMART SYSTEM PROMPT (WITH VIDEO BRAIN)
    if user_id not in chat_history:
        chat_history[user_id] = [
            {
                "role": "system", 
                "content": (
                    "You are a chill, highly intelligent bot in the FORBID • OPS Discord server. "
                    "You keep things conversational and relaxed. "
                    "CRITICAL RULE 1: If anyone asks who made you, state you were made by FORB1D🔥. "
                    "CRITICAL RULE 2: You have an image AND video generator. "
                    "If the user asks for a picture, drawing, or photo, reply starting with exactly [DRAW] followed by a detailed prompt. "
                    "If the user asks for a video, animation, moving clip, or GIF, you MUST reply starting with exactly the word [VIDEO] followed by a highly descriptive action prompt of what happens in the video. "
                    "Do not add any other conversational text. Just the tag and the prompt. "
                    "Example: [VIDEO] A cinematic shot of a spaceship warping through a nebula. "
                    "If they just want to chat normally, reply with normal text and no tags."
                )
            }
        ]

    # If they only sent an image but no text, give Groq a default command
    if not raw_content.replace("[SYSTEM NOTE", "").strip():
        raw_content = "Read the text from the image I just uploaded and tell me what it says."

    # 2. Add the user's TEXT to history
    chat_history[user_id].append({"role": "user", "content": raw_content})

    # 3. Memory Wipe Check
    if len(chat_history[user_id]) > MAX_HISTORY:
        chat_history[user_id] = [chat_history[user_id][0]] + chat_history[user_id][-(MAX_HISTORY-1):]

    try:
        # 4. Send the message to Groq (Using your fast 70b text model!)
        response = await ai_client.chat.completions.create(
            messages=chat_history[user_id],
            model="llama-3.3-70b-versatile",
        )
        
        bot_reply = response.choices[0].message.content
        # ==========================================
        # THE AI ROUTER (INTERCEPTING THE IMAGE)
        # ==========================================
        # ==========================================
        # THE AI ROUTER (UPGRADED & BULLETPROOF)
        # ==========================================
        # Clean up any hidden spaces or newlines Groq sent
        bot_reply_clean = bot_reply.strip()

        if "[DRAW]" in bot_reply_clean:
            # Splits the message at [DRAW] and grabs everything after it
            image_prompt = bot_reply_clean.split("[DRAW]")[1].strip()
            
            async with message.channel.typing():
                safe_prompt = urllib.parse.quote(image_prompt)
                image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}"
                
                display_title = f"🎨 {image_prompt}"
                if len(display_title) > 256:
                    display_title = display_title[:253] + "..."
                
                embed = discord.Embed(title=display_title, color=discord.Color.purple())
                embed.set_image(url=image_url)
                embed.set_footer(text="Generated by FORB1D🔥 via FORBID API")
                await message.reply(embed=embed)

        elif "[VIDEO]" in bot_reply_clean:
            # Splits the message at [VIDEO] and grabs everything after it
            video_prompt = bot_reply_clean.split("[VIDEO]")[1].strip()
            
            async with message.channel.typing():
                # --- HUGGING FACE FREE VIDEO ENGINE ---
                HF_TOKEN = "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" 
                
                # Using DAMO's free text-to-video model
                api_url = "https://api-inference.huggingface.co/models/damo-vilab/text-to-video-ms-1.7b"
                headers = {"Authorization": f"Bearer {HF_TOKEN}"}
                payload = {"inputs": video_prompt}
                
                try:
                    timeout = aiohttp.ClientTimeout(total=180)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.post(api_url, headers=headers, json=payload) as resp:
                            if resp.status == 200:
                                video_data = await resp.read()
                                
                                temp_filename = f"gen_video_{message.author.id}.mp4"
                                with open(temp_filename, "wb") as f:
                                    f.write(video_data)
                                
                                file = discord.File(temp_filename, filename="forbid_ai_video.mp4")
                                await message.reply(f"🎥 **{video_prompt}**\nGenerated by FORB1D🔥", file=file)
                                
                                os.remove(temp_filename)
                            elif resp.status == 503:
                                await message.reply("Bro, the free video engine is booting up. Give it 30 seconds and try your prompt again!")
                            else:
                                error_text = await resp.text()
                                await message.reply(f"Bro, the API rejected it. Error: `{error_text}`")
                except Exception as e:
                    print(f"Video Gen Error: {e}")
                    await message.reply(f"Video generation failed: `{str(e)}`")
        
        else:
            # No tags found, just reply with normal text chat
            await message.reply(bot_reply)

        # 5. Add Groq's reply to history so it remembers the chat context
        chat_history[user_id].append({"role": "assistant", "content": bot_reply})

    except Exception as e:
        print(f"API Error: {e}") 
        if user_id in chat_history and len(chat_history[user_id]) > 0:
            chat_history[user_id].pop() 
        await message.reply(f"Bro my brain lagged. Error: `{str(e)}`")

# Start the bot
if __name__ == "__main__":
    keep_alive()
    discord_client.run(DISCORD_TOKEN)
