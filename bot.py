"""
This file is a part of Yagoo Bot <https://yagoo.pleb.moe/>
Copyright (C) 2020-present  ProgrammingPleb

Yagoo Bot is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Yagoo Bot is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Yagoo Bot.  If not, see <http://www.gnu.org/licenses/>.
"""

import discord
import asyncio
import json
import yaml
import logging
import sys
import os
from discord_slash import SlashCommand
from discord_slash.model import ButtonStyle
from discord_slash.context import ComponentContext
from discord_slash.utils.manage_components import create_actionrow, create_button, wait_for_component
from discord.ext import commands, tasks
from yagoo.scrapers.infoscraper import channelInfo
from yagoo.cogs.chUpdater import chCycle
from yagoo.cogs.subCycle import StreamCycle
from yagoo.cogs.msCycle import msCycle, milestoneNotify
from yagoo.cogs.dblUpdate import guildUpdate
from yagoo.cogs.premiereCycle import PremiereCycle
from yagoo.cogs.twtCycle import twtCycle
from yagoo.lib.botUtils import getRoles, subPerms, creatorCheck, userWhitelist
from yagoo.lib.dataUtils import refreshWebhook, botdb, dbTools
from yagoo.lib.prompts import botError
from yagoo.commands.subscribe import defaultSubtype, subCategory, subCustom, sublistDisplay, unsubChannel
from yagoo.commands.general import botAssignRoles, botHelp, botGetInfo, botTwt
from yagoo.commands.slash import YagooSlash

init = False

with open("data/settings.yaml") as f:
    settings = yaml.load(f, Loader=yaml.SafeLoader)

if settings["logging"] == "info":
    logging.basicConfig(level=logging.INFO, filename='status.log', filemode='w', format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
elif settings["logging"] == "debug":
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.FileHandler('status.log', 'w', 'utf-8')], format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')

async def determine_prefix(bot: commands.Bot, message: discord.Message):
    db = await botdb.getDB()
    guild = message.guild
    if guild:
        if await botdb.checkIfExists(str(message.guild.id), "server", "prefixes", db):
            return commands.when_mentioned_or((await botdb.getData(str(message.guild.id), "server", ("prefix",), "prefixes", db))["prefix"])(bot, message)
        else:
            return commands.when_mentioned_or(settings["prefix"])(bot, message)
    else:
        return commands.when_mentioned_or(settings["prefix"])(bot, message)

bot = commands.Bot(command_prefix=determine_prefix, help_command=None)
bot.remove_command('help')
slash = SlashCommand(bot, True)
if settings["slash"]:
    bot.add_cog(YagooSlash(bot, slash, settings["prefix"]))

class updateStatus(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.updateStatus.start()
    
    def cog_unload(self):
        self.updateStatus.stop()

    @tasks.loop(minutes=20)
    async def updateStatus(self):
        channels = await botdb.getAllData("channels", ("id",))
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name=f'over {len(channels)} VTubers'))
        await asyncio.sleep(10*60)
        guildCount = 0
        for guilds in self.bot.guilds:
            guildCount += 1
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name=f'over {guildCount} servers'))

@bot.event
async def on_ready():
    global init
    if not init:
        guildCount = 0
        for guilds in bot.guilds:
            guildCount += 1
        if os.path.exists("ext/commands/custom.py"):
            from yagoo.commands.custom import customCommands
            bot.add_cog(customCommands(bot))
            print("Loaded custom commands!")
        print(f"Yagoo Bot now streaming in {guildCount} servers!")
        if settings["dblPublish"]:
            bot.add_cog(guildUpdate(bot, settings["dblToken"]))
        if settings["channel"]:
            bot.add_cog(chCycle(bot))
        if settings["twitter"]["enabled"]:
            bot.add_cog(twtCycle(bot))
        if settings["notify"]:
            bot.add_cog(StreamCycle(bot))
        if settings["premiere"]:
            bot.add_cog(PremiereCycle(bot))
        if settings["milestone"]:
            bot.add_cog(msCycle(bot))
        bot.add_cog(updateStatus(bot))
        init = True
    else:
        print("Reconnected to Discord!")

@bot.event
async def on_guild_remove(server):
    logging.info(f'Got removed from a server, cleaning up server data for: {str(server)}')
    await botdb.deleteRow(str(server), "server", "servers")

@bot.command(alias=['h'])
async def help(ctx): # pylint: disable=redefined-builtin
    db = await botdb.getDB()
    if await botdb.checkIfExists(str(ctx.guild.id), "server", "prefixes", db):
        prefix = (await botdb.getData(str(ctx.guild.id), "server", ("prefix",), "prefixes", db))["prefix"]
    else:
        prefix = settings["prefix"]
    await ctx.send(embed=await botHelp(prefix))

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
async def unsubscribe(ctx, *, channel = None):
    await unsubChannel(ctx, bot, channel)

@unsubscribe.error
async def unsub_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

@bot.command(aliases=['subdefault'])
@commands.check(subPerms)
async def subDefault(ctx):
    await defaultSubtype(ctx, bot)

@subDefault.error
async def subdef_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

@bot.command(aliases=["subs", "subslist", "subscriptions", "subscribed"])
@commands.check(subPerms)
async def sublist(ctx):
    await sublistDisplay(ctx, bot)

@sublist.error
async def sublist_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)
        
@bot.command(aliases=["getinfo"])
async def info(ctx, *, name: str = None):
    if name is None:
        await ctx.send(embed=await botError(ctx, "Missing Arguments"))
        return
    await botGetInfo(ctx, bot, name)

@bot.command()
@commands.check(subPerms)
async def follow(ctx, accLink: str = None):
    await botTwt.follow(ctx, bot, accLink)

@follow.error
async def follow_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

@bot.command()
@commands.check(subPerms)
async def unfollow(ctx):
    await botTwt.unfollow(ctx, bot)

@unfollow.error
async def follow_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

@bot.command()
@commands.check(subPerms)
async def prefix(ctx: commands.Context, *, prefix: str = None):
    db = await botdb.getDB()
    if prefix is None:
        if await botdb.checkIfExists(str(ctx.guild.id), "server", "prefixes", db):
            prefix = (await botdb.getData(str(ctx.guild.id), "server", ("prefix",), "prefixes", db))["prefix"]
        else:
            prefix = settings["prefix"]
            await botdb.addData((str(ctx.guild.id), prefix), ("server", "prefix"), "prefixes", db)
        embed = discord.Embed(title="Current Prefix", description=f"The current prefix for this server is: `{prefix}`")
        await ctx.send(embed=embed)
        return
    await botdb.addData((str(ctx.guild.id), prefix), ("server", "prefix"), "prefixes", db)
    
    embed = discord.Embed(title="Prefix Updated!", description=f"The prefix for this server is now `{prefix}`.", color=discord.Colour.green())
    await ctx.send(embed=embed)

@bot.command()
@commands.check(creatorCheck)
async def test(ctx):
    db = await botdb.getDB()
    print(await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), ("livestream", "milestone", "premiere"), db))

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
@commands.check(userWhitelist)
async def omedetou(ctx: commands.Context):
    await ctx.message.delete()

    replyID = ctx.message.reference.message_id
    replyMsg = await ctx.channel.fetch_message(replyID)

    await replyMsg.reply("おめでとう！", mention_author=False)

@bot.command()
@commands.check(creatorCheck)
async def ytchCount(ctx):
    await ctx.send(f"Yagoo Bot has {len(await botdb.getAllData('channels'))} channels in the database.")

@bot.command()
@commands.check(subPerms)
async def chRefresh(ctx: commands.Context):
    buttonRow = create_actionrow(create_button(style=ButtonStyle.blue, label="No"), create_button(style=ButtonStyle.red, label="Yes"))
    qmsg = await ctx.send("Are you sure to refresh this channel's webhook URL?", components=[buttonRow])
    
    def check(res):
        return res.author == ctx.message.author and res.channel == ctx.channel

    try:
        res: ComponentContext = await wait_for_component(bot, qmsg, buttonRow, check, 30)
    except asyncio.TimeoutError:
        await qmsg.delete()
        await ctx.message.delete()
    else:
        if res.component["label"] == "Yes":
            await res.defer()
            await refreshWebhook(bot, ctx.guild, ctx.channel)
            await res.edit_origin(content="The webhook URL has been refreshed for this channel.", components=[])
        else:
            await qmsg.delete()
            await ctx.message.delete()

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
    
    await ctx.send(f"Yagoo Bot is now live in {totalGuilds} servers!")

bot.run(settings["token"])
