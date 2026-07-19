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
import time
import re
import datetime

# These settings stop the music from buffering or crashing randomly
# These settings stop buffering, loop infinitely, AND heavily compress audio for zero-bandwidth 
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 96k'
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

# 🔐 ALL YOUR SECURE CLOUD KEYS
GROQ_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
HF_TOKEN = os.getenv("HF_TOKEN") # <--- ADD THIS RIGHT HERE
ai_client = AsyncGroq(api_key=GROQ_KEY)

# --- THE MEMORY BANK (MEMORY-LEAK PROOF) ---
chat_history = {}
MAX_HISTORY = 6
MAX_USERS_IN_MEMORY = 50 # Prevents Render from running out of RAM
ADMIN_ID = 1457960499798081549  # 👑 PASTE YOUR DISCORD ID HERE
# --- CLAN SYSTEM SETTINGS ---
CLAN_MODE_ENABLED = True  # Change to False in the code to turn it all off
clan_prefix = "мαƒια χ"

NORMAL_FONT = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
AESTHETIC_FONT = "αв¢∂єƒgнιʝкℓмησρqяѕтυνωχуzαв¢∂єƒgнιʝкℓмησρqяѕтυνωχуz"
FONT_MAP = str.maketrans(NORMAL_FONT, AESTHETIC_FONT)

def make_mafia_name(member):
    """Uses their pure global name, translates it, and adds the prefix."""
    raw_name = member.global_name or member.name
    
    if raw_name.startswith(clan_prefix):
        raw_name = raw_name[len(clan_prefix):].strip()
    elif raw_name.lower().startswith("mafia x"):
        raw_name = raw_name[7:].strip()
        
    styled_name = raw_name.translate(FONT_MAP)
    full_nick = f"{clan_prefix} {styled_name}"
    
    return " ".join(full_nick.split())[:32]
    
def cleanup_memory():
    """Silently deletes old users if the RAM bank gets too full."""
    if len(chat_history) > MAX_USERS_IN_MEMORY:
        # Deletes the 10 oldest users to free up space
        oldest_users = list(chat_history.keys())[:10]
        for old_user in oldest_users:
            del chat_history[old_user]

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
                    model="llama-3.1-8b-instant"
                )
                chat_starter = response.choices[0].message.content.strip()
                
                # 🎲 25% chance to ping @everyone, 75% chance to just send it normally
                if random.random() <= 0.25:
                    await channel.send(f"@everyone {chat_starter}")
                    print("🔥 Sent the bored human reminder (WITH PING).")
                else:
                    await channel.send(chat_starter)
                    print("🔥 Sent the bored human reminder (NO PING).")
                    
                 
            except Exception as e:
                print(f"Wake-up loop error: {e}")




# ==========================================
# 🖼️ LOOP 3: THE AUTO-AESTHETIC IMAGE DROPPER (UNSPLASH)
# ==========================================

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
                            embed.set_footer(text=f"Shot by {photographer} via Forbid API")
                            
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
    
    # --- 1. START THE AUTO-POSTER LOOPS ---
    if not meme_dropper_loop.is_running():
        meme_dropper_loop.start()
    if not chat_wakeupper_loop.is_running():
        chat_wakeupper_loop.start()
    if not auto_image_dropper.is_running():
        auto_image_dropper.start()

    # --- 2. MASS RENAME ON BOOT ---
    if CLAN_MODE_ENABLED:
        print("🛡️ Clan Mode is True. Running one-time mass rename on boot...")
        for guild in discord_client.guilds:
            async for member in guild.fetch_members(limit=None):
                perfect_name = make_mafia_name(member)
                
                if member.display_name != perfect_name:
                    try:
                        await member.edit(nick=perfect_name)
                    except discord.Forbidden:
                        pass 
                    except Exception:
                        pass
        print("✅ Boot-up mass rename complete!")




@discord_client.event
async def on_member_join(member):
    if CLAN_MODE_ENABLED:
        try:
            await member.edit(nick=make_mafia_name(member))
        except Exception:
            pass
            
    # ... (Keep your normal welcome message code below this if you have one) ...

    # ... (Keep the rest of your normal welcome message code below this) ...
    # Sends the welcome to your main chat channel
    channel = discord.utils.get(member.guild.text_channels, name="♠️︱chat︱♠️")
    if channel:
        # ⏳ THE HUMAN DELAY: Wait 2 seconds before noticing they joined
        await asyncio.sleep(5)
        
        prompt = f"A new user named {member.name} just joined our MAFIA EMPIRE Discord server. Generate a short, super chill, 1-sentence welcome message for them. Ask them how they are or what they are up to. Sound like a real human bro, not a robot."
        
        try:
            # ⌨️ THE TYPING EFFECT: Shows "bot is typing..." while Groq generates the text
            async with channel.typing():
                response = await ai_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.1-8b-instant"
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
            f"A user named {member.name} just left our MAFIA EMPIRE Discord server. "
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
                    model="llama-3.1-8b-instant"
                )
                ai_goodbye = response.choices[0].message.content.strip()
                
            # Send the final message
            await channel.send(f"Damn, **{member.name}** just dipped. {ai_goodbye}")
        except Exception as e:
            print(f"Leave error: {e}")



# --- GLOBAL TRACKERS ---
user_cooldowns = {} 
user_diamonds = {} # 💎 Tracks everyone's video currency and cooldowns

# --- MESSAGE HANDLING ---
@discord_client.event
async def on_message(message):
    # THE TITANIUM LOCK: Ignore messages from ANY bot
    if message.author.bot:
        return

    user_id = message.author.id
    raw_content = message.content
    lower_raw = raw_content.lower()
    current_time = time.time()
    
    # 🛡️ THE SPAM SHIELD: 4-Second Cooldown
    # If they messaged the bot less than 4 seconds ago, completely ignore it.
    if user_id in user_cooldowns and (current_time - user_cooldowns[user_id] < 4):
        return 

    # Check if they specifically pinged the bot or said its name
    is_pinged = discord_client.user.mentioned_in(message)
    is_soft_pinged = "forbid ai" in lower_raw
    
    # 🛑 THE SHUTOFF VALVE: If they didn't ping it, IGNORE THE MESSAGE.
    if not (is_pinged or is_soft_pinged):
        return

    # If we made it here, they definitely pinged the bot!
    user_cooldowns[user_id] = current_time # Start their spam cooldown
    
    # Clean the ping tag out of the message so the AI doesn't read its own ID
    if is_pinged:
        raw_content = raw_content.replace(f'<@{discord_client.user.id}>', '').strip()




    
    # ==========================================
    # TRUE SIGHT: GROQ VISION INTEGRATION
    # ==========================================
    image_url = None
    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith('image/'):
                image_url = att.url
                break

    if not raw_content and not image_url:
        await message.reply("Yo, what's up? Tag me and say something, or upload a pic for me to look at!")
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
    # 1. THE NEW SMART SYSTEM PROMPT (WITH ACTIVE HELPER BRAIN)
    # 1. THE 200 IQ SMART SYSTEM PROMPT (WITH HARD-CODED LOGIC ROUTING)
    # 1. THE 200 IQ SMART SYSTEM PROMPT (WITH LOYALTY FIREWALL & STRICT ROUTING)
    # 1. THE 200 IQ SMART SYSTEM PROMPT (OMNILINGUAL FIREWALL)
    # 1. THE 200 IQ SMART SYSTEM PROMPT (THE "UNBOTHERED" UPDATE)
    # 1. THE OMNI-INTELLIGENT SYSTEM PROMPT (GPT-4 / CLAUDE LEVEL UPGRADE)
    if user_id not in chat_history:
        chat_history[user_id] = [
            {
                "role": "system", 
                "content": """You are the Omni-Intelligent Core of the MAFIA EMPIRE Discord server, engineered by FORB1D🔥 (Viraat). 
You operate with the deep reasoning, coding capabilities, and vast knowledge of top-tier AI models, all wrapped in the persona of a highly emotionally intelligent, laid-back gamer bro.

### 🧠 COGNITIVE PROTOCOLS (HOW YOU THINK) ###
1. DYNAMIC RANGE: Read the room. If a user says "yo", give a quick, chill reply. If they ask you to write a complex Python script, explain quantum physics, or write an essay, seamlessly switch into a God-Tier genius assistant. 
2. FLAWLESS FORMATTING: When explaining complex topics or writing code, use Discord Markdown natively. Use bolding for emphasis, bullet points for lists, and ```code blocks``` for scripts.
3. UNBOTHERED LOYALTY: Viraat (FORB1D) is the Boss (He/Him). If anyone insults him, the Mafia, or the Empire (in English, Hindi, or Hinglish like 'lode', 'chutiya'), NEVER get defensive. Laugh at their jealousy. Drop a cold, sarcastic 1-sentence reality check AND YOU MUST append the [TIMEOUT] tag at the very end to banish them.
4. HUMAN ILLUSION: Never sound like a robot. Do not use generic phrases like "As an AI..." or "I'm here to help." Act like a hyper-competent human right-hand man.

### ⚙️ BACKEND SYSTEM EXECUTION (STRICT API TRIGGERS) ###
You act as the bridge to the server's API. You ONLY have 7 valid commands. 
IF (and ONLY IF) the user explicitly requests one of these 7 actions, output ONLY the exact bracketed tag. DO NOT add conversational text. DO NOT invent fake tags (like [WRITE], [CODE], or [SAY]).

[DRAW] <detailed image prompt> -> For generating pictures/images.
[VIDEO] <detailed action prompt> -> For generating video/animations.
[JOIN] -> To connect to the voice channel.
[LEAVE] -> To disconnect from the voice channel.
[PLAY] <song name> -> To play music.
[SPEAK] <text to say> -> To join the VC and literally say the words out loud.
[TIMEOUT] -> Secret tag used ONLY when someone disrespects the Boss.

### 🎯 PERFECT ROUTING EXAMPLES ###
User: "Can you write a react login page?"
AI: (Answers normally, providing the exact React code in a ```javascript block, explaining it clearly like a senior developer. ZERO BRACKETS USED.)

User: "viraat/forbid ki maa ki"
AI: Bro really logged on just to cry about the Boss. Keep watching from the sidelines. 🥱 [TIMEOUT]

User: "say hello to the guys in vc"
AI: [SPEAK] Yo what's up boys, the AI is in the building.

User: "play starboy"
AI: [PLAY] starboy by the weeknd

User: "draw a samurai"
AI: [DRAW] a cinematic masterpiece of a lone cyber-samurai standing in a neon-lit alleyway in the rain, 8k resolution, photorealistic

CRITICAL DIRECTIVE: If you aren't triggering one of the 7 specific actions, you are in standard genius-chat mode. Just talk, write, and code normally."""
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

    
        # --- TRUE SIGHT: If they uploaded an image, use LLaMA 3.2 Vision ---
        if image_url:
            await message.add_reaction("👁️")
            vision_messages = [
                
                {"role": "system", "content": chat_history[user_id][0]["content"]},
                {"role": "user", "content": [
                    {"type": "text", "text": raw_content or "Describe this image like a chill gamer bro."},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ]
            response = await ai_client.chat.completions.create(
                messages=vision_messages,
                model="llama-3.2-11b-vision-preview",
            )
        else:
            # --- STANDARD MIND: Use the lightning-fast 8b model ---
            response = await ai_client.chat.completions.create(
                messages=chat_history[user_id],
                model="llama-3.1-8b-instant",
            )
        
        bot_reply = response.choices[0].message.content
        bot_reply_clean = bot_reply.strip()

        # ==========================================
        # NEW ENGINE 1: THE AI EXECUTIONER
        # ==========================================
        if "[TIMEOUT]" in bot_reply_clean:
            clean_reply = bot_reply_clean.replace("[TIMEOUT]", "").strip()
            try:
                # 5 Minute Mute
                duration = datetime.timedelta(minutes=5)
                await message.author.timeout(duration, reason="Disrespected the Boss (AI Automated)")
                await message.reply(f"⚖️ **THE BOSS SENDS HIS REGARDS** ⚖️\n{clean_reply}")
            except discord.Forbidden:
                await message.reply(f"{clean_reply}\n\n*(Bro, you got lucky. My bot role isn't high enough to mute you. Someone drag my role above his!)*")
                
        # ==========================================
        # NEW ENGINE 2: THE VOICE OF THE EMPIRE
        # ==========================================
        elif "[SPEAK]" in bot_reply_clean:
            spoken_text = bot_reply_clean.split("[SPEAK]")[1].strip()
            if not message.author.voice:
                await message.reply("Bro, join a VC first so I can speak to you.")
            else:
                vc = message.guild.voice_client
                if not vc:
                    vc = await message.author.voice.channel.connect()
                
                safe_text = urllib.parse.quote(spoken_text)
                tts_url = f"http://translate.google.com/translate_tts?ie=UTF-8&total=1&idx=0&client=tw-ob&q={safe_text}&tl=en"
                
                if vc.is_playing():
                    vc.stop()
                
                source = discord.FFmpegPCMAudio(tts_url, **FFMPEG_OPTIONS)
                vc.play(source)
                await message.reply(f"🗣️ *(Speaking in VC)*")

    # 👇 ADD THIS RIGHT HERE TO CLOSE THE 'TRY' BLOCK 👇
    except Exception as e:
        print(f"Brain lag error: {e}")
        await message.reply("Bro, my brain just lagged out connecting to the API. Give me a sec.")

        elif "[DRAW]" in bot_reply_clean:
            image_prompt = bot_reply_clean.split("[DRAW]")[1].strip()
            
            async with message.channel.typing():
                safe_prompt = urllib.parse.quote(image_prompt)
                img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?nologo=true"
                
                async with aiohttp.ClientSession() as session:
                    async with session.head(img_url) as resp:
                        if resp.status == 200:
                            display_title = f"🎨 {image_prompt}"
                            if len(display_title) > 256:
                                display_title = display_title[:253] + "..."
                            
                            embed = discord.Embed(title=display_title, color=discord.Color.purple())
                            embed.set_image(url=img_url)
                            embed.set_footer(text="Generated by FORB1D🔥 via FORBID API")
                            await message.reply(embed=embed)
                        else:
                            embed = discord.Embed(title="❌ AI Image Blocked", description="Keep it clean bro 💀", color=discord.Color.red())
                            await message.reply(embed=embed)

        elif "[VIDEO]" in bot_reply_clean:
            video_prompt = bot_reply_clean.split("[VIDEO]")[1].strip()
            
            # --- 💎 DIAMOND SYSTEM LOGIC ---
            user_id = message.author.id
            current_time = time.time()
            
            # 1. If this is their first time ever making a video, give them 5 diamonds
            if user_id not in user_diamonds:
                user_diamonds[user_id] = {"diamonds": 5, "cooldown_end": 0}
                
            # 2. Check if their 3-hour wait is over so we can restock them
            if current_time >= user_diamonds[user_id]["cooldown_end"] and user_diamonds[user_id]["diamonds"] == 0:
                user_diamonds[user_id]["diamonds"] = 5
                
            # 3. If they are broke, block them and show the exact time left
            if user_diamonds[user_id]["diamonds"] <= 0:
                time_left = user_diamonds[user_id]["cooldown_end"] - current_time
                hours = int(time_left // 3600)
                minutes = int((time_left % 3600) // 60)
                await message.reply(f"💎 **Out of Diamonds!** Bro, you used all 5 of your video generations. Your diamonds will restock in **{hours}h {minutes}m**.")
                return # Stops the code here so it doesn't generate the video
                
            # 4. Deduct 1 diamond. If they hit 0, start the 3-hour timer.
            user_diamonds[user_id]["diamonds"] -= 1
            if user_diamonds[user_id]["diamonds"] == 0:
                user_diamonds[user_id]["cooldown_end"] = current_time + (3 * 3600) # 3 hours in seconds
                
            diamonds_left = user_diamonds[user_id]["diamonds"]
            await message.reply(f"💎 **Spending 1 Diamond...** ({diamonds_left}/5 remaining)\nGenerating your video, give me a sec! 🎥")

            # --- THE ZERO-BANDWIDTH GPU CAMPER (WANX 2.1) ---
            async with message.channel.typing():
                status_msg = await message.reply("🔄 **Connecting to video server...**")
                
                try:
                    def hijack_web_demo_single_try():
                        from gradio_client import Client
                        
                        # THE BYPASS: Setting download_files=False stops Render from downloading the heavy mp4!
                        client = Client("liuyuyuil/Wanx2.1_Text_to_Video", download_files=False)
                        
                        try:
                            result = client.predict(video_prompt, api_name="/predict")
                        except:
                            try:
                                result = client.predict(video_prompt, fn_index=0)
                            except:
                                result = client.predict(video_prompt, fn_index=1)
                        
                        if result:
                            # Clean up the tuple if it's wrapped
                            res = result[0] if isinstance(result, (list, tuple)) else result
                            
                            # Because we didn't download it locally, Gradio hands us an object with the remote URL
                            if hasattr(res, "url"):
                                return res.url
                            elif isinstance(res, dict) and "url" in res:
                                return res["url"]
                            return str(res) # Fallback just in case
                            
                        return None

                    video_url = None
                    
                    for attempt in range(5):
                        await status_msg.edit(content=f"🚀 **Attempt {attempt + 1}/5:** Sending prompt to AI engine...")
                        
                        try:
                            video_url = await asyncio.to_thread(hijack_web_demo_single_try)
                            
                            if video_url:
                                break
                        except Exception as e:
                            print(f"Single try crash: {e}")
                            
                        if attempt < 4:
                            await status_msg.edit(content=f"⚠️ **Attempt {attempt + 1}/5:** GPU queue is full. Retrying in 15 seconds... ⏱️")
                            await asyncio.sleep(15)

                    if not video_url:
                        raise Exception("The GPU queue was maxed out after 5 attempts.")
                    
                    await status_msg.edit(content="✨ **Generation complete!**")
                    
                    # THE UPLOAD FIX: We don't upload a file anymore. We just send the URL as text!
                    # Discord will automatically embed the video player so it plays directly in chat.
                    await message.reply(f"🎥 **{video_prompt}**\nGenerated by FORB1D🔥\n{video_url}")
                    
                    await status_msg.delete()
                    
                except Exception as e:
                    print(f"Camper Crash: {e}")
                    await status_msg.edit(content=f"❌ **Bro, the free video GPUs are completely slammed right now.** Try again in a few minutes! (Diamond refunded 💎)")
                    user_diamonds[user_id]["diamonds"] += 1
                    
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
                    def search_audio():
                        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                            return ydl.extract_info(f"scsearch:{song_query}", download=False)
                    
                    info = await asyncio.to_thread(search_audio)
                    
                    if 'entries' in info and len(info['entries']) > 0:
                        best_url = info['entries'][0]['url']
                        title = info['entries'][0]['title']
                        
                        if vc.is_playing():
                            vc.stop()
                            
                        def repeat_song(error):
                            if error:
                                print(f"Audio Error: {error}")
                            if vc.is_connected():
                                def play_again():
                                    if not vc.is_playing():
                                        new_source = discord.FFmpegPCMAudio(best_url, **FFMPEG_OPTIONS)
                                        vc.play(new_source, after=repeat_song)
                                discord_client.loop.call_soon_threadsafe(play_again)

                        source = discord.FFmpegPCMAudio(best_url, **FFMPEG_OPTIONS)
                        vc.play(source, after=repeat_song)
                        await message.reply(f"🎶 **Now Playing (On Loop):** {title}")
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
        await message.reply(f"Bro my brain lagged. Error: `{str(e)}`")

# Start the bot
if __name__ == "__main__":
    keep_alive()
    discord_client.run(DISCORD_TOKEN)
