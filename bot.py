import discord
import os
import asyncio
import urllib.parse
from groq import AsyncGroq
from flask import Flask
from threading import Thread
from discord.ext import tasks
import aiohttp # Make sure this is at the very top!
import yt_dlp
import random

# These settings stop the music from buffering or crashing randomly
# These settings stop the music from buffering AND loop it infinitely
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -stream_loop -1',
    'options': '-vn'
}
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'default_search': 'ytsearch',
    'quiet': True
}

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
intents.members = True # THIS ALLOWS THE BOT TO SEE NEW JOINS
discord_client = discord.Client(intents=intents)

# You only need these two keys! No image API key needed.
GROQ_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ai_client = AsyncGroq(api_key=GROQ_KEY)
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY") # <--- Add this!

# --- THE MEMORY BANK ---
chat_history = {}
MAX_HISTORY = 12 

# --- 20-MINUTE AUTO-MEME & CHAT STARTER ---
# ==========================================
# 🎪 LOOP 1: THE 20-MINUTE MEME DROPPER
# ==========================================
@tasks.loop(minutes=20)
async def meme_dropper_loop():
    for channel in discord_client.get_all_channels():
        if channel.name == "♠️︱memes︱♠️" and isinstance(channel, discord.TextChannel):
            try:
                # Rip a clean, random meme from Reddit via a free API
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://meme-api.com/gimme') as resp:
                        if resp.status == 200:
                            meme_data = await resp.json()
                            meme_url = meme_data.get('url', '')
                            
                            if meme_url:
                                await channel.send(meme_url)
                                print("🔥 Successfully dropped a fresh meme.")
                break 
            except Exception as e:
                print(f"Meme loop error: {e}")


# ==========================================
# 🗣️ LOOP 2: THE 1-HOUR "BORED/LONELY" CHAT WAKE-UP
# ==========================================
@tasks.loop(hours=1)
async def chat_wakeupper_loop():
    for channel in discord_client.get_all_channels():
        if channel.name == "♠️︱chat︱♠️" and isinstance(channel, discord.TextChannel):
            try:
                # Tell Groq to act like a bored human looking for someone to talk to
                prompt = (
                    "Generate a short, single-sentence Discord message. "
                    "Act like a chill teenager who is bored, lonely, and wants someone to talk to because the chat is totally dead. "
                    "Examples of the vibe: 'chat is dead, anyone alive?' or 'bored af, someone entertain me' or 'is anyone even awake rn'. "
                    "Talk like a real gamer bro. Do NOT sound like an AI or a bot. Max 15 words. No cringe hashtags or emojis."
                )
                
                response = await ai_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile"
                )
                chat_starter = response.choices[0].message.content.strip()
                
                # 🎲 25% chance to ping @everyone, 75% chance to just send it normally
                if random.random() <= 0.25:
                    await channel.send(f"@everyone {chat_starter}")
                    print("🔥 Sent the bored human reminder (WITH PING).")
                else:
                    await channel.send(chat_starter)
                    print("🔥 Sent the bored human reminder (NO PING).")
                    
                break 
            except Exception as e:
                print(f"Wake-up loop error: {e}")




# ==========================================
# 🖼️ LOOP 3: THE AUTO-AESTHETIC IMAGE DROPPER (UNSPLASH)
# ==========================================
# 🔑 Put your Unsplash Access Key here!
UNSPLASH_ACCESS_KEY = "YOUR_UNSPLASH_ACCESS_KEY_HERE"

@tasks.loop(minutes=40)
async def auto_image_dropper():
    # Defines the search topics for Unsplash
    image_channels = {
        "𓆩︱pfps︱𓆪": "portrait, cyberpunk, anime, aesthetic",
        "𓆩︱banners︱𓆪": "landscape, neon, city, luxury, wallpaper",
        "𓆩︱icons︱𓆪": "minimalist, logo, glowing, dark, abstract"
    }

    for channel in discord_client.get_all_channels():
        if channel.name in image_channels and isinstance(channel, discord.TextChannel):
            try:
                search_query = image_channels[channel.name]
                orientation = "landscape" if "banners" in channel.name else "squarish"
                
                api_url = f"https://api.unsplash.com/photos/random"
                params = {
                    "client_id": UNSPLASH_ACCESS_KEY, # <--- It grabs the key from the environment here
                    "query": search_query,
                    "orientation": orientation
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            image_url = data["urls"]["regular"]
                            photographer = data["user"]["name"]
                            portfolio = data["user"]["links"]["html"]
                            
                            # Build the Aesthetic Embed
                            embed = discord.Embed(
                                title="🔥 Fresh Drop", 
                                description="Steal this for your profile.", 
                                color=discord.Color.dark_theme()
                            )
                            embed.set_image(url=image_url)
                            embed.set_footer(text=f"Shot by {photographer} via Unsplash")
                            
                            await channel.send(embed=embed)
                        else:
                            print(f"Unsplash API rejected the request for {channel.name}. Code: {resp.status}")
                
                # Wait 5 seconds before checking the next channel
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Auto-image loop error in {channel.name}: {e}")

# ==========================================
# 🎮 LOOP 4: THE 2-HOUR GAMING NEWS & TIPS DROP
# ==========================================

# --- START ALL LOOPS WHEN BOT IS READY ---
@meme_dropper_loop.before_loop
@chat_wakeupper_loop.before_loop
@auto_image_dropper.before_loop

async def before_loops():
    await discord_client.wait_until_ready()
    
@discord_client.event
async def on_ready():
    print(f'🔥 WE LIVE! Logged in as {discord_client.user}')
    
    # Start the meme dropper
    if not meme_dropper_loop.is_running():
        meme_dropper_loop.start()
        
    # Start the chat wake-upper
    if not chat_wakeupper_loop.is_running():
        chat_wakeupper_loop.start()
        
    # Start the new auto-image dropper
    if not auto_image_dropper.is_running():
        auto_image_dropper.start()




@discord_client.event
async def on_member_join(member):
    # Sends the welcome to your main chat channel
    channel = discord.utils.get(member.guild.text_channels, name="♠️︱chat︱♠️")
    if channel:
        # ⏳ THE HUMAN DELAY: Wait 2 seconds before noticing they joined
        await asyncio.sleep(5)
        
        prompt = f"A new user named {member.name} just joined our FORBID • OPS Discord server. Generate a short, super chill, 1-sentence welcome message for them. Ask them how they are or what they are up to. Sound like a real human bro, not a robot."
        
        try:
            # ⌨️ THE TYPING EFFECT: Shows "bot is typing..." while Groq generates the text
            async with channel.typing():
                response = await ai_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile"
                )
                ai_welcome = response.choices[0].message.content.strip()
                
            # Send the final message
            await channel.send(f"Yoo <@{member.id}>! {ai_welcome}")
        except Exception as e:
            print(f"Welcome error: {e}")

@discord_client.event
async def on_member_remove(member):
    # Sends the goodbye to your main chat channel
    channel = discord.utils.get(member.guild.text_channels, name="♠️︱chat︱♠️")
    if channel:
        # ⏳ THE HUMAN DELAY: Wait 2 seconds before reacting
        await asyncio.sleep(5)
        
        prompt = (
            f"A user named {member.name} just left our FORBID • OPS Discord server. "
            "Generate a short, chill, 1-sentence goodbye message about them leaving. "
            "Make it funny, slightly dramatic, or just a cool 'peace out'. "
            "Talk like a chill teenager, sound like a real human bro, not a robot."
        )
        
        try:
            # ⌨️ THE TYPING EFFECT: Shows "bot is typing..."
            async with channel.typing():
                # ⏳ Force the typing status to stay on screen for 2 seconds
                await asyncio.sleep(2)
                
                response = await ai_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile"
                )
                ai_goodbye = response.choices[0].message.content.strip()
                
            # Send the final message
            await channel.send(f"Damn, **{member.name}** just dipped. {ai_goodbye}")
        except Exception as e:
            print(f"Leave error: {e}")

# --- MESSAGE HANDLING ---
@discord_client.event
async def on_message(message):
    # THE TITANIUM LOCK: Ignore messages from ANY bot, including itself
    if message.author.bot:
        return

    # Check if the bot was specifically tagged
    is_pinged = discord_client.user.mentioned_in(message)
    raw_content = message.content

    # If the bot wasn't pinged, it will randomly "eavesdrop"
    if not is_pinged:
        # Only eavesdrop in the main chat, and only if someone asks a question (?)
        if message.channel.name == "♠️︱chat︱♠️" and "?" in raw_content:
            # Jump in 30% of the time so it feels natural, not annoying
            if random.random() > 0.30:
                return 
        else:
            return # Ignore normal messages without pings
    else:
        # If they DID ping the bot, clean the tag out of the message
        raw_content = raw_content.replace(f'<@{discord_client.user.id}>', '').strip()
    
    # ==========================================
    # 🎧 THE MUSIC ENGINE ROUTER
    # ==========================================
    lower_content = raw_content.lower()

    if lower_content.startswith("join me"):
        if message.author.voice:
            channel = message.author.voice.channel
            if not message.guild.voice_client:
                await channel.connect()
                await message.reply("🔥 I'm in the VC bro. Tell me what to play.")
            else:
                await message.reply("Bro, I'm already in a channel!")
        else:
            await message.reply("You gotta join a Voice Channel first so I know where to go!")
        return 

    elif lower_content.startswith("leave"):
        if message.guild.voice_client:
            await message.guild.voice_client.disconnect()
            await message.reply("Peace out ✌️ Left the VC.")
        else:
            await message.reply("I'm not even in a voice channel bruh.")
        return 

    elif lower_content.startswith("play "):
        song_query = raw_content[5:].strip()
        
        # Check if user is in a VC
        if not message.author.voice:
            await message.reply("Join a VC first so I can play this for you!")
            return
            
        # Join if not already in one
        vc = message.guild.voice_client
        if not vc:
            vc = await message.author.voice.channel.connect()

        await message.reply(f"🔍 Searching for: `{song_query}`...")
        
        try:
            # We use scsearch (SoundCloud) to completely bypass YouTube's anti-bot wall!
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"scsearch:{song_query}", download=False)
                
                if 'entries' in info and len(info['entries']) > 0:
                    best_url = info['entries'][0]['url']
                    title = info['entries'][0]['title']
                    
                    # Stop currently playing song if there is one
                    if vc.is_playing():
                        vc.stop()
                        
                    # Play the new audio stream
                    source = discord.FFmpegPCMAudio(best_url, **FFMPEG_OPTIONS)
                    vc.play(source)
                    await message.reply(f"🎶 **Now Playing:** {title}")
                else:
                    await message.reply("Bro, I couldn't find that song.")
        except Exception as e:
            print(f"Music Error: {e}")
            await message.reply(f"Music engine crashed: `{str(e)}`")
            
        return # Stops the message from going to the AI 

    # ==========================================
    # IMAGE SCANNER (Checking for uploads)
    # ==========================================
    
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
                    "CRITICAL RULE 3: YOU ARE A DJ. If the user asks you to join the voice channel (e.g. 'hop in', 'join'), reply with exactly [JOIN]. "
                    "If they ask you to leave (e.g. 'get out', 'stop'), reply with exactly [LEAVE]. "
                    "If they ask you to play a specific song, reply with exactly [PLAY] followed by the song name. "
                    "CRITICAL RULE 4: MOODS & INFINITE MIXES. If the user asks for a vibe or mood (e.g., 'play sad songs', 'play hype music'), DO NOT pick a short song. You MUST search for a massive mix by appending '10 hour mix' to the query (e.g., [PLAY] 10 Hour Sad Bollywood Lofi Mix). "
                    "Do not add any other conversational text when using these tags. Just the tag and the prompt. "
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
                image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?nologo=true"
                
                # ⬇️ THE UPGRADE: We check the API response BEFORE sending it to Discord
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            # It's a valid image! Download and send it natively.
                            image_data = await resp.read()
                            temp_filename = f"gen_image_{message.author.id}.png"
                            
                            with open(temp_filename, "wb") as f:
                                f.write(image_data)
                            
                            display_title = f"🎨 {image_prompt}"
                            if len(display_title) > 256:
                                display_title = display_title[:253] + "..."
                            
                            file = discord.File(temp_filename, filename="art.png")
                            embed = discord.Embed(title=display_title, color=discord.Color.purple())
                            embed.set_image(url="attachment://art.png")
                            embed.set_footer(text="Generated by FORB1D🔥 via FORBID API")
                            
                            await message.reply(embed=embed, file=file)
                            os.remove(temp_filename)
                            
                        else:
                            # If it's blocked (NSFW/Explicit), intercept it and show an error embed
                            embed = discord.Embed(
                                title="❌ AI Image Blocked",
                                description=f"**Prompt:** `{image_prompt}`\n\n**Reason:** The generator rejected this. It might be explicit, NSFW, or against the safety filters.",
                                color=discord.Color.red()
                            )
                            embed.set_footer(text="Keep it clean bro 💀")
                            await message.reply(embed=embed)

        elif "[VIDEO]" in bot_reply_clean:
            # Splits the message at [VIDEO] and grabs everything after it
            video_prompt = bot_reply_clean.split("[VIDEO]")[1].strip()
            
            async with message.channel.typing():
                # --- HUGGING FACE FREE VIDEO ENGINE ---
                HF_TOKEN = "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" 
                api_url = "https://api-inference.huggingface.co/models/damo-vilab/text-to-video-ms-1.7b"
                headers = {"Authorization": f"Bearer {HF_TOKEN}"}
                payload = {"inputs": video_prompt}
                
                try:
                    timeout = aiohttp.ClientTimeout(total=180)
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
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
                                        break
                                        
                                    elif resp.status == 503:
                                        await message.reply("Bro, the free video engine is booting up. Give it 30 seconds and try your prompt again!")
                                        break
                                    else:
                                        error_text = await resp.text()
                                        await message.reply(f"Bro, the API rejected it. Error: `{error_text}`")
                                        break
                        except aiohttp.ClientConnectorError as e:
                            print(f"Network glitch on attempt {attempt + 1}: {e}")
                            if attempt == max_retries - 1:
                                await message.reply("Bro, my server's internet is lagging right now. Try again in a minute!")
                            await asyncio.sleep(2)
                            
                except Exception as e:
                    print(f"Video Gen Error: {e}")
                    await message.reply(f"Video generation failed: `{str(e)}`")

        elif "[JOIN]" in bot_reply_clean:
            if message.author.voice:
                channel = message.author.voice.channel
                if not message.guild.voice_client:
                    await channel.connect()
                    await message.reply("🔥 I'm in the VC bro. Tell me what to play.")
                else:
                    await message.reply("Bro, I'm already in a channel!")
            else:
                await message.reply("You gotta join a Voice Channel first so I know where to go!")

        elif "[LEAVE]" in bot_reply_clean:
            if message.guild.voice_client:
                await message.guild.voice_client.disconnect()
                await message.reply("Peace out ✌️ Left the VC.")
            else:
                await message.reply("I'm not even in a voice channel bruh.")

        elif "[PLAY]" in bot_reply_clean:
            song_query = bot_reply_clean.split("[PLAY]")[1].strip()
            
            if not message.author.voice:
                await message.reply("Join a VC first so I can play this for you!")
            else:
                vc = message.guild.voice_client
                if not vc:
                    vc = await message.author.voice.channel.connect()

                await message.reply(f"🔍 AI DJ searching for: `{song_query}`...")
                
                try:
                    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                        info = ydl.extract_info(f"scsearch:{song_query}", download=False)
                        
                        if 'entries' in info and len(info['entries']) > 0:
                            best_url = info['entries'][0]['url']
                            title = info['entries'][0]['title']
                            
                            if vc.is_playing():
                                vc.stop()
                                
                            source = discord.FFmpegPCMAudio(best_url, **FFMPEG_OPTIONS)
                            vc.play(source)
                            await message.reply(f"🎶 **Now Playing:** {title}")
                        else:
                            await message.reply("Bro, I couldn't find that song.")
                except Exception as e:
                    print(f"Music Error: {e}")
                    await message.reply(f"Music engine crashed: `{str(e)}`")
        
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
