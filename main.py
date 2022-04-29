#!/bin/python
import os, json, random, discord, youtube_dl
from dotenv import load_dotenv
from discord.ext import commands
from discord.utils import get
from fuzzywuzzy import fuzz

######################################### SETUP ############################################

with open("db.json") as f:

    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')

    db = json.load(f)
    queuue = []
    bot = commands.Bot(command_prefix='!')
    bot.remove_command('help')

######################################### EVENTS ###########################################

@bot.event
async def on_ready():
    print(f'{bot.user.name} is on!')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Command not found!. To see all the commands, type !help')

##################################### GENERAL COMMANDS #####################################

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send(f":wave: Hello {ctx.author.name}!")

@bot.command(name="roll")
async def roll(ctx):
    await ctx.send(f':8ball: Your number is: {random.randint(1, 6)}!')

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f':ping_pong: SpanishBot ping: {int(bot.latency)}ms')

##################################### DATABASE FUNCTIONS ####################################

def write_db(action, entry, definition):
    with open("db.json", "w") as f:

        if action == "add":
            db[entry] = definition
        elif action == "delete":
            del db[entry]

        json.dump(db, f, indent=4)

def check_entry(entry):
    with open("db.json") as f: db = json.load(f)
    return 1 if entry in db else 0

def refresh_db():
    global db
    with open("db.json") as f: db = json.load(f)

##################################### DATABASE COMMANDS #####################################

@bot.command(name="add")
async def add(ctx, entry, definition):

    if check_entry(entry):
        await ctx.send(f':x: {entry} already exists!')
        return
    
    write_db("add", entry, definition)
    write_db("add", definition, entry)
    await ctx.send(f':white_check_mark: Word "{entry}" with translation "{definition}" added!')

@bot.command(name="update")
async def update(ctx, entry, definition):
    
    if not check_entry(entry):
        await ctx.send(f':x: {entry} does not exist!')
        return
        
    write_db("add", entry, definition)
    await ctx.send(f':heavy_check_mark: Word "{entry}" with translation "{definition}" updated!')

@bot.command(name="delete")
async def delete(ctx, entry):

    if not check_entry(entry):
        await ctx.send(f':x: {entry} does not exist!')
        return
            
    write_db("delete", entry)
    await ctx.send(f':heavy_check_mark: Word "{entry}" deleted!')

@bot.command(name="search")
async def search(ctx, *, entry):

    if not check_entry(entry):
        max = 0; result = ""
        for word in db:
            if fuzz.ratio(word, entry) > max:
                max = fuzz.ratio(word, entry)
                result = word
        await ctx.send(f':question: Did you mean "{result}"?')
        return

    await ctx.send(f':mag: "{entry}" means "{db[entry]}"')

##################################### ADMIN COMMANDS ##########################################

@bot.command(name="kick")
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f':hammer: Kicked {member.name} {reason}')

@bot.command(name="ban")
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f':no_entry_sign: Banned {member.name} {reason}')

@bot.command(name="unban")
@commands.has_permissions(administrator=True)
async def unban(ctx, *, member):
    banned_users = await ctx.guild.bans()
    member_name, member_discriminator = member.split('#')

    for ban_entry in banned_users:
        user = ban_entry.user

        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await ctx.guild.unban(user)
            await ctx.send(f':blush: Unbanned {user.name}')
            return
    
    await ctx.send(f':x: {member} is not banned in this server!')

#################################### MUSIC FUNCTIONS ##########################################

def start_playing(queue, voice_client, player):

    queue.insert(0, player)

    i = 0
    while i < len(queue):
        try:
            voice_client.play(queue[i])
        except Exception as e:
            print(e)
            pass
        i += 1
    queue = []

##################################### MUSIC COMMANDS #########################################

@bot.command(name="play")
async def play(ctx, url):
    global queuue
    YDL_OPTIONS = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

    voice = get(bot.voice_clients, guild=ctx.guild)
    
    try:
        if voice and not voice.is_connected():
            voice = await ctx.message.author.voice.channel.connect()
        elif voice and voice.is_connected():
            await voice.move_to(ctx.message.author.voice.channel)
        elif not voice:
            voice = await ctx.message.author.voice.channel.connect()
    except Exception as e:
        print(e)

    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        URL = info['formats'][0]['url']

    player = discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS)

    try:
        if len(queuue) == 0:

            await ctx.send(f'**Music: **<{url}>')
            start_playing(queuue, voice, player)

        else:

            await ctx.send(f'**Queue: **<{url}>')          
            queuue.append(player)
    except Exception as e:
        print(e)

@bot.command(name="pause")
async def stop(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_playing():
        voice.pause()
        await ctx.send("Stopped the music!")
    else:
        await ctx.send("No music is playing!")
    
@bot.command(name="resume")
async def start(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and not voice.is_playing():
        voice.resume()
        await ctx.send("Resumed the music!")
    else:
        await ctx.send("Music is playing!")

@bot.command(name="leave")
async def leave(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        voice.stop()
        await voice.disconnect()
        await ctx.send("Left the voice chat!")
    else:
        await ctx.send("I am not in a voice chat!")

@bot.command(name="volume")
async def volume(ctx, volume: int):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        voice.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")
    else:
        await ctx.send("I am not in a voice chat!")

@bot.command(name="queue")
async def queue(ctx):
    global queuue
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await ctx.send(queuue)
    else:
        await ctx.send("I am not in a voice chat!")

@bot.command(name="skip")
async def skip(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        voice.stop()
        
        await ctx.send("Skipped the music!")
    else:
        await ctx.send("I am not in a voice chat!")

@bot.command(name="love")
async def play(ctx):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

    channel = ctx.message.author.voice.channel
    voice_client = await channel.connect()

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        file = ydl.extract_info('https://www.youtube.com/watch?v=dQw4w9WgXcQ', download=False)
        path = file['formats'][0]['url']

    voice_client.play(discord.FFmpegPCMAudio(path, **FFMPEG_OPTIONS), after=lambda e: print('Player error: %s' % e) if e else None)

################################### FUNCTIONALITY COMMANDS #####################################

@bot.command(name="help")
async def help(ctx):
    await ctx.send('```md\n'
                   f'Hello {ctx.author.name}! I am SpanishBot, a bot that helps you learn Spanish!\n\n'
                   '#------------------- Dictionary commands ----------------#\n\n'
                   f'+ To add an entry, type !add <word> <translation>\n'
                   f'+ To update an entry, type !update <word> <translation>\n'
                   f'+ To delete an entry, type !delete <word>\n'
                   f'+ To search for an entry, type !search <word>\n\n'
                   '#--------------------- Other commands -------------------#\n\n'
                   f'+ To roll a dice, type !roll\n'
                   f'+ To see the bot\'s ping, type !ping\n\n'
                   '#--------------------- Admin commands -------------------#\n\n'
                   f'+ To kick a member, type !kick <member> <reason>\n'
                   f'+ To ban a member, type !ban <member> <reason>\n'
                   f'+ To unban a member, type !unban <tag> \n\n'
                   '#---------------------- Music comands -------------------#\n\n'
                   '+ To play a song, type !play <url>\n'
                   '+ To pause the music, type !pause\n'
                   '+ To resume the music, type !resume\n'
                   '+ To leave the voice chat, type !leave\n\n'
                   '#------------------------ Secret ------------------------#\n\n'
                     '+ To see the bot\'s secret, type !love\n'
                   '```')

############################################ RUN ###############################################

bot.run(TOKEN)
