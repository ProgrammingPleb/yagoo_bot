import aiohttp
import discord
import asyncio
import json
import yaml
import logging
import sys
import platform
from discord import Webhook, AsyncWebhookAdapter
from discord_slash import SlashCommand
from discord.ext import commands
from ext.infoscraper import channelInfo
from ext.cogs.subCycle import StreamCycle, streamcheck
from ext.cogs.msCycle import msCycle, milestoneNotify
from ext.cogs.dblUpdate import guildUpdate
from ext.cogs.chUpdater import chCycle
from ext.cogs.scrapeCycle import ScrapeCycle
from ext.cogs.premiereCycle import PremiereCycle
from ext.share.botUtils import subPerms, creatorCheck
from ext.share.dataGrab import getSubType, getwebhook
from ext.share.prompts import botError, subCheck
from ext.commands.subscribe import subCategory, subCustom
from ext.commands.general import botHelp, botSublist, botGetInfo
from ext.commands.slash import YagooSlash

init = False

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

with open("data/settings.yaml") as f:
    settings = yaml.load(f, Loader=yaml.SafeLoader)

if settings["logging"] == "info":
    logging.basicConfig(level=logging.INFO, filename='status.log', filemode='w', format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
elif settings["logging"] == "debug":
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.FileHandler('status.log', 'w', 'utf-8')], format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')

bot = commands.Bot(command_prefix=commands.when_mentioned_or(settings["prefix"]), help_command=None)
bot.remove_command('help')
if settings["slash"]:
    slash = SlashCommand(bot, True)
    bot.add_cog(YagooSlash(bot, slash))

@bot.event
async def on_ready():
    global init
    if not init:
        guildCount = 0
        for guilds in bot.guilds:
            guildCount += 1
        print(f"Yagoo Bot now streaming in {guildCount} servers!")
        await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name='other Hololive members'))
        if settings["dblPublish"]:
            bot.add_cog(guildUpdate(bot, settings["dblToken"]))
        if settings["channel"]:
            bot.add_cog(ScrapeCycle(bot, settings["logging"]))
            await asyncio.sleep(30)
            bot.add_cog(chCycle(bot))
        if settings["notify"]:
            bot.add_cog(StreamCycle(bot))
        if settings["premiere"]:
            bot.add_cog(PremiereCycle(bot))
        if settings["milestone"]:
            bot.add_cog(msCycle(bot))
        init = True
    else:
        print("Reconnected to Discord!")

@bot.event
async def on_guild_remove(server):
    logging.info(f'Got removed from a server, cleaning up server data for: {str(server)}')
    with open("data/servers.json") as f:
        servers = json.load(f)
    servers.pop(str(server.id), None)
    with open("data/servers.json", "w") as f:
        json.dump(servers, f, indent=4)

@bot.command(alias=['h'])
async def help(ctx): # pylint: disable=redefined-builtin
    await ctx.send(embed=await botHelp())

@bot.command(aliases=['subdefault'])
@commands.check(subPerms)
async def subDefault(ctx):
    await getSubType(ctx, 1, bot)

@subDefault.error
async def subdef_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

@bot.command(aliases=['sub'])
@commands.check(subPerms)
async def subscribe(ctx, *, customUser = None):
    if customUser is None:
        await subCategory(ctx, bot)
    else:
        await subCustom(ctx, bot, customUser)

@subscribe.error
async def sub_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

@bot.command(aliases=["unsub"])
@commands.check(subPerms)
async def unsubscribe(ctx):
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    with open("data/servers.json") as f:
        servers = json.load(f)
    
    unsubmsg = await ctx.send("Loading subscription list...")

    if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
        uInput = await subCheck(ctx, bot, unsubmsg, 2, "Unsubscribe")
    else:
        uInput = {
            "success": True,
            "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
        }
    
    if not uInput["success"]:
        await unsubmsg.delete()
        await ctx.message.delete()
        return
    
    if len(uInput["subType"]) > 1:
        subDisp = "livestream"
    else:
        subDisp = uInput["subType"][0]
    
    try:
        len(servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp])
    except KeyError:
        await unsubmsg.edit(content="There are no subscriptions on this channel.", embed=None)
        return

    multi = False
    sublist = []
    templist = []
    if len(servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]) > 9:
        for sub in servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]:
            if len(templist) < 9:
                templist.append(sub)
            else:
                sublist.append(templist)
                templist = [sub]
        sublist.append(templist)
        multi = True
    elif len(servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]) > 0 and len(servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]) < 10:
        for sub in servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]:
            sublist.append(sub)
    else:
        await unsubmsg.edit(content="There are no subscriptions on this channel.", embed=None)
        return
    
    pagepos = 0
    while True:
        dispstring = ""
        dispnum = 1
        if multi:
            subProc = sublist[pagepos]
            for sub in subProc:
                ytch = channels[sub]
                dispstring += f'{dispnum}. {ytch["name"]}\n'
                dispnum += 1
            if pagepos == 0:
                dispstring += f'\nA. Unsubscribe to all channels\nN. Go to next page\nX. Cancel'
            elif pagepos == len(sublist) - 1:
                dispstring += f'\nA. Unsubscribe to all channels\nB. Go to previous page\nX. Cancel'
            else:
                dispstring += f'\nA. Unsubscribe to all channels\nN. Go to next page\nB. Go to previous page\nX. Cancel'
        else:
            subProc = sublist
            for sub in sublist:
                ytch = channels[sub]
                dispstring += f'{dispnum}. {ytch["name"]}\n'
                dispnum += 1
            dispstring += f'A. Unsubscribe to all channels\nX. Cancel'
        
        usembed = discord.Embed(title="Unsubscribe from channel:", description=dispstring)
        await unsubmsg.edit(content=None, embed=usembed)

        def check(m):
            return m.content.lower() in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'n', 'b', 'x'] and m.author == ctx.author

        while True:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await unsubmsg.delete()
                await ctx.message.delete()
                return
            else:
                if msg.content in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await getwebhook(bot, servers, ctx.guild, ctx.channel)
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await msg.delete()
                    for subType in uInput["subType"]:
                        try:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].remove(subProc[int(msg.content) - 1])
                        except ValueError:
                            ytch = channels[subProc[int(msg.content) - 1]]
                            await unsubmsg.edit(content=f'Couldn\'t unsubscribe {subType} notifications from: {ytch["name"]}!', embed=None)
                        else:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)]["notified"].pop(subProc[int(msg.content) - 1], None)
                            ytch = channels[subProc[int(msg.content) - 1]]
                            await unsubmsg.edit(content=f'Unsubscribed from: {ytch["name"]}.', embed=None)
                    with open("data/servers.json", "w") as f:
                        json.dump(servers, f, indent=4)
                    await ctx.message.delete()
                    return
                if msg.content.lower() == 'a':
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await getwebhook(bot, servers, ctx.guild, ctx.channel)
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    for subType in uInput["subType"]:
                        servers[str(ctx.guild.id)][str(ctx.channel.id)][subType] = []
                    servers[str(ctx.guild.id)][str(ctx.channel.id)]["notified"] = {}
                    with open("data/servers.json", "w") as f:
                        json.dump(servers, f, indent=4)
                    await unsubmsg.edit(content=f'This channel is now unsubscribed from any YouTube channels.', embed=None)
                    await msg.delete()
                    await ctx.message.delete()
                    return
                if multi:
                    if msg.content.lower() == 'n' and pagepos < len(sublist) - 1:
                        await msg.delete()
                        pagepos += 1
                        break
                    elif msg.content.lower() == 'b' and pagepos > 0:
                        await msg.delete()
                        pagepos -= 1
                        break
                elif msg.content.lower() == 'x':
                    await msg.delete()
                    await unsubmsg.delete()
                    await ctx.message.delete()
                    return
                else:
                    await msg.delete()

@unsubscribe.error
async def unsub_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

@bot.command(aliases=["getinfo"])
async def info(ctx, *, name: str = None):
    if name is None:
        await ctx.send(embed=await botError(ctx, "Missing Arguments"))
        return
    await botGetInfo(ctx, bot, name)

@bot.command(aliases=["subs", "subslist", "subscriptions", "subscribed"])
@commands.check(subPerms)
async def sublist(ctx):
    await botSublist(ctx, bot)

@sublist.error
async def sublist_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

@bot.command()
@commands.check(creatorCheck)
async def test(ctx):
    await ctx.send("Rushia Ch. \u6f64\u7fbd\u308b\u3057\u3042")

@bot.command(aliases=["livestats", "livestat"])
@commands.check(subPerms)
async def livestatus(ctx):
    loadmsg = await ctx.send("Loading info...")
    await streamcheck(ctx, True)
    await loadmsg.delete()

@bot.command()
@commands.check(creatorCheck)
async def mscheck(ctx, vtuber):
    with open("data/channels.json") as f:
        channels = json.load(f)

    ytch = await channelInfo(vtuber)
    if ytch["roundSubs"] < 1000000:
        subtext = f'{int(ytch["roundSubs"] / 1000)}K Subscribers'
    else:
        if ytch["roundSubs"] == ytch["roundSubs"] - (ytch["roundSubs"] % 1000000):
            subtext = f'{int(ytch["roundSubs"] / 1000000)}M Subscribers'
        else:
            subtext = f'{ytch["roundSubs"] / 1000000}M Subscribers'
    msDict = {
        vtuber: {
            "name": ytch["name"],
            "image": ytch["image"],
            "banner": ytch["mbanner"],
            "msText": subtext
        }
    }
    await milestoneNotify(msDict, bot, True)
    await ctx.send(file=discord.File(f'milestone/generated/{vtuber}.png'))

@bot.command()
@commands.check(creatorCheck)
async def nstest(ctx):
    with open("data/servers.json") as f:
        servers = json.load(f)
    
    live = await streamcheck()
    whurl = await getwebhook(bot, servers, ctx.guild, ctx.channel)

    for livech in live:
        async with aiohttp.ClientSession() as session:
            embed = discord.Embed(title=f'{live[livech]["videoTitle"]}', url=f'https://youtube.com/watch?v={live[livech]["videoId"]}')
            embed.description = f'Started streaming {live[livech]["timeText"]}'
            embed.set_image(url=f'https://img.youtube.com/vi/{live[livech]["videoId"]}/maxresdefault.jpg')
            webhook = Webhook.from_url(whurl, adapter=AsyncWebhookAdapter(session))
            await webhook.send(f'New livestream from {live[livech]["name"]}!', embed=embed, username=live[livech]["name"], avatar_url=live[livech]["image"])

@bot.command()
@commands.check(creatorCheck)
async def postas(ctx, vtuber, *, text):
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    with open("data/servers.json") as f:
        servers = json.load(f)
    whurl = await getwebhook(bot, servers, ctx.guild, ctx.channel)
    ytch = await channelInfo(channels[vtuber]["channel"])
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(whurl, adapter=AsyncWebhookAdapter(session))
        await webhook.send(text, username=ytch["name"], avatar_url=ytch["image"])

@bot.command()
@commands.check(creatorCheck)
async def removeChannel(ctx, channelId):
    removed = False

    with open("data/servers.json") as f:
        servers = json.load(f)
    
    for server in servers:
        try:
            if channelId in servers[server]:
                servers[server].pop(channelId)
                removed = True
        except Exception as e:
            await ctx.send(f"Unable to remove {channelId} from servers.json!")

    if removed:
        await ctx.send(f"Removed {channelId} from servers.json!")
    else:
        await ctx.send(f"{channelId} does not exist in servers.json!")
        return
    
    with open("data/servers.json", "w") as f:
        json.dump(servers, f, indent=4)

@bot.command()
@commands.check(creatorCheck)
async def omedetou(ctx: commands.Context):
    replyID = ctx.message.reference.message_id
    replyMsg = await ctx.channel.fetch_message(replyID)

    await replyMsg.reply("おめでとう！", mention_author=False)

@bot.command()
@commands.check(creatorCheck)
async def ytchCount(ctx):
    chCount = 0

    with open("data/channels.json") as f:
        channels = json.load(f)
    for channel in channels:
        chCount += 1
    
    await ctx.send(f"Yagoo Bot has {chCount} channels in the database.")

@bot.command(aliases=["maint", "shutdown", "stop"])
@commands.check(creatorCheck)
async def maintenance(ctx):
    await ctx.send("Changing to maintenance mode...\nBot will shut down in 5 minutes.")
    logging.info("Maintenance mode started. Shutting down in 5 minutes.")
    ctdwn = ["5 minutes", "4 minutes", "3 minutes", "2 minutes", "1 minute"]
    for x in range(5):
        if x != 4:
            await bot.change_presence(status=discord.Status.idle, activity=discord.Activity(type=discord.ActivityType.playing, name=f'Bot will undergo maintenance in {ctdwn[x]}.'))
        else:
            await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.playing, name=f'Bot will undergo maintenance in {ctdwn[x]}.'))
        await asyncio.sleep(60)
    logging.info("Shutting down!")
    await bot.change_presence(status=discord.Status.offline)
    bot.remove_cog(StreamCycle())
    bot.remove_cog(msCycle())
    logging.info("Stopped Stream Checker.")
    dev = bot.get_user(256009740239241216)
    await dev.send("Bot has shutdown.")
    await bot.close()
    logging.info("Logged out.")
    sys.exit()

@bot.command(aliases=["gCount", "gcount", "guildcount"])
@commands.check(creatorCheck)
async def guildCount(ctx):
    totalGuilds = 0
    for x in bot.guilds:
        totalGuilds += 1
    
    await ctx.send(f"Yagoo bot is now live in {totalGuilds} servers!")

bot.run(settings["token"])
