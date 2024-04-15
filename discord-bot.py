import discord
from discord.ext import commands
from collections import deque
import asyncio
import yt_dlp
import os

# Define a queue for each channel
queues = {}

# Define downloads folder
DL_Folder = "C:/Files/Programs/discord-bot/dl/"

# Define intents
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

# Set up the bot
bot = commands.Bot(command_prefix='!', intents = intents)

# Function to check url and get the audio URL, and check if the file exists
async def get_url_audio_url(search):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': DL_Folder + '%(id)s-#%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(search, download=False)
        duration = info_dict.get('duration', None)
        video_id = info_dict.get('id', None)
        video_title = info_dict.get('title', None)
        if duration and duration <= 2400:  # 40 minutes
            filename = f"{video_id}-#{video_title}.webm"
            for file in os.listdir('C:/Files/Programs/discord-bot/dl/'):
                if file.startswith(video_id) and file.endswith('.webm'):
                    print(f'This video already exists: {file}')
                    return file  # Return the existing file path

            # Download the file since it doesn't exist
            print(f'This video is being downloaded: {filename}')
            ydl.download([info_dict['webpage_url']])
            return filename  # Return the new file path
    return None

# Function to search video and get the audio URL, and check if the file exists
async def get_search_audio_url(search):
    # Use yt-dlp to search for the top result on YouTube
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': DL_Folder + '%(id)s-#%(title)s.%(ext)s',
        'default_search': 'ytsearch1:',
        'quiet': True,
        'no_warnings': True,
        'source_address': '0.0.0.0'  # IPv4 only
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(search, download=False)
        if 'entries' in info_dict:
            # Take the first result from the search
            video_info = info_dict['entries'][0]
        else:
            # Direct video without search results
            video_info = info_dict

        duration = video_info.get('duration', None)
        video_id = video_info.get('id', None)
        video_title = video_info.get('title', None)

        if duration and duration <= 2400:  # 40 minutes
            filename = f"{video_id}-#{video_title}.webm"
            for file in os.listdir('C:/Files/Programs/discord-bot/dl/'):
                if file.startswith(video_id) and file.endswith('.webm'):
                    print(f'This video already exists: {file}')
                    return file  # Return the existing file path

            # Download the file since it doesn't exist
            print(f'This video is being downloaded: {filename}')
            ydl.download([info_dict['webpage_url']])
            return filename  # Return the new file path
    return None

# Command to join voice channel
@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    channel = ctx.author.voice.channel
    await channel.connect()

# Command to leave voice channel
@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    await ctx.voice_client.disconnect()

# Function to start playing the next song in the queue
async def play_next(ctx):
    if queues[ctx.channel.id]:
        audio_url = queues[ctx.channel.id].popleft()
        ctx.voice_client.play(discord.FFmpegPCMAudio(DL_Folder + audio_url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        # Create the embed message
        temp_title = audio_url.split("-#")[1]
        temp_title = temp_title.split(".webm")[0]
        embed = discord.Embed(title="Now Playing", description=f"{temp_title}", color=0x00ff00)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title='Queue is empty', description='No songs are currently in the queue.', color=0xff0000)
        await ctx.send(embed=embed, delete_after=2)

# Command to play a YouTube video
@bot.command(name='play', help='Plays a video from YouTube')
async def play(ctx, *, search):
    # Check if 'search' is a URL or a search term
    if search == "" or search == " ":
        embed = discord.Embed(title='Error', description='There is nothing to search', color=0xff0000)
        await ctx.send(embed=embed, delete_after=2)
        return
    if search.startswith('https://'):
        audio_url = await get_url_audio_url(search)
    else:
        audio_url = await get_search_audio_url(search)
    
    # Check if the bot is already connected to the voice channel
    if ctx.voice_client is None:
        if ctx.author.voice and ctx.author.voice.channel:
            await ctx.author.voice.channel.connect()
        else:
            embed = discord.Embed(title='Error', description='You are not connected to a voice channel', color=0xff0000)
            await ctx.send(embed=embed, delete_after=2)
            return

    # Create the embed message
    temp_title = audio_url.split("-#")[1]
    temp_title = temp_title.split(".webm")[0]

    # If a song is currently playing, add the new song to the queue
    if ctx.voice_client.is_playing():
        if ctx.channel.id not in queues:
            queues[ctx.channel.id] = deque()
        queues[ctx.channel.id].append(audio_url)
        embed = discord.Embed(title="Queue", description=f"{temp_title} added to the queue!", color=0x00ff00)
        await ctx.send(embed=embed)
    else:
        # If nothing is playing, start playing the new song
        ctx.voice_client.play(discord.FFmpegPCMAudio(DL_Folder + audio_url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        embed = discord.Embed(title="Now Playing", description=f"{temp_title}", color=0x00ff00)
        await ctx.send(embed=embed)

@bot.command(name='queue', help='Shows the current song queue')
async def queue(ctx):
    if ctx.channel.id in queues and queues[ctx.channel.id]:
        # Create the embed object
        embed = discord.Embed(title='Current Queue', description='', color=0x00ff00)
        for idx, title in enumerate(queues[ctx.channel.id]):
            # Assuming title is in the format 'video_id-title'
            video_id, video_title = title.split('-#')
            video_title, video_ext = video_title.split(".webm")
            embed.add_field(name=f'{idx + 1}.', value=video_title, inline=False)
        
        await ctx.send(embed=embed)
    else:
        # Send a simple embed message if the queue is empty
        embed = discord.Embed(title='Queue is empty', description='No songs are currently in the queue.', color=0xff0000)
        await ctx.send(embed=embed, delete_after=2)

# Command to pause audio
@bot.command(name='pause', help='Pause the song')
async def pause(ctx):
    voice_client = ctx.message.channel.voice_client
    if voice_client.is_playing():
        await ctx.send(f"Pausing song")
        voice_client.pause()
    else:
        embed = discord.Embed(title='Error', description='Nothing is currently playing', color=0xff0000)
        await ctx.send(embed=embed, delete_after=2)

# Command to resume audio
@bot.command(name='resume', help='Resume the song')
async def pause(ctx):
    voice_client = ctx.message.channel.voice_client
    if voice_client.is_paused():
        await ctx.send(f"Resuming song")
        voice_client.resume()
    else:
        embed = discord.Embed(title='Error', description='Nothing was playing', color=0xff0000)
        await ctx.send(embed=embed, delete_after=2)

@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.channel.voice_client
    if voice_client.is_playing():
        await ctx.send(f"Stopping song")
        voice_client.stop()
        voice_client.pause()
    else:
        embed = discord.Embed(title='Error', description='Nothing is currently playing', color=0xff0000)
        await ctx.send(embed=embed, delete_after=2)

@bot.command(name='skip', help='Skips the song')
async def stop(ctx):
    voice_client = ctx.message.channel.voice_client
    if voice_client.is_playing():
        await ctx.send(f"Skipping song")
        voice_client.stop()
    else:
        embed = discord.Embed(title='Error', description='Nothing is currently playing', color=0xff0000)
        await ctx.send(embed=embed, delete_after=2)

# Command to clean bot's messages
@bot.command(name='clean', help='Cleans bot\'s and user\'s command messages')
async def clean(ctx, limit: int = 100):
    def is_command(m):
        # Check if the message is from the bot or starts with the bot's command prefix
        return m.author == bot.user or m.content.startswith(bot.command_prefix)
    
    deleted = await ctx.channel.purge(limit=limit, check=is_command)
    await ctx.send(f'Cleaned up {len(deleted)} message(s)', delete_after=2)

@bot.command(name='ping', help='Sound check')
async def ping(ctx):
    await ctx.send('Pong!')

@bot.event
async def on_command(ctx):
    print(f'Command received: {ctx.message.content}')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    # Ignore messages sent by the bot
    if message.author == bot.user:
        return

    # Process commands
    await bot.process_commands(message)

# Run the bot - Change token before use
bot.run('DISCORD_API_TOKEN')