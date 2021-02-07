import json
import discord
import asyncio
import aiohttp
from discord.ext import commands
from ..infoscraper import FandomScrape, channelInfo
from ..share.botUtils import chunks
from ..share.dataGrab import getwebhook
from ..share.prompts import subCheck, searchConfirm, searchPrompt

async def subHolo(ctx: commands.Context, bot: commands.Bot):
    listmsg = await ctx.send("Loading channels list...")

    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    csplit = []
    for split in chunks(channels, 9):
        csplit.append(split)
    pagepos = 0
    
    while True:
        picknum = 1
        pickstr = ""
        picklist = []
        for split in csplit[pagepos]:
            ytch = csplit[pagepos][split]
            if ytch["category"] == "Hololive":
                pickstr += f'{picknum}. {ytch["name"]}\n'
                picklist.append(split)
                picknum += 1
        if pagepos == 0:
            pickstr += f'\nA. Subscribe to all channels\nN. Go to next page\nX. Cancel'
        elif pagepos == len(csplit) - 1:
            pickstr += f'\nA. Subscribe to all channels\nB. Go to previous page\nX. Cancel'
        else:
            pickstr += f'\nA. Subscribe to all channels\nN. Go to next page\nB. Go to previous page\nX. Cancel'

        listembed = discord.Embed(title="Subscribe to channel:", description=pickstr)
        await listmsg.edit(content=None, embed=listembed)

        def check(m):
            return m.content.lower() in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'n', 'b', 'x'] and m.author == ctx.author

        while True:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await listmsg.delete()
                await ctx.message.delete()
                return
            if msg.content in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                with open("data/servers.json") as f:
                    servers = json.load(f)
                await getwebhook(bot, servers, ctx.guild, ctx.channel)
                with open("data/servers.json") as f:
                    servers = json.load(f)
                await msg.delete()
                if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
                    uInput = await subCheck(ctx, bot, listmsg, 1, csplit[pagepos][picklist[int(msg.content) - 1]]["name"])
                else:
                    uInput = {
                        "success": True,
                        "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
                    }
                lastSubbed = False

                if not uInput["success"]:
                    await listmsg.delete()
                    await ctx.message.delete()
                    return

                for subType in uInput["subType"]:
                    if picklist[int(msg.content) - 1] not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                        servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(picklist[int(msg.content) - 1])
                    else:
                        if len(uInput["subType"]) > 1 and not lastSubbed:
                            lastSubbed = True
                        else:
                            ytch = csplit[pagepos][picklist[int(msg.content) - 1]]
                            await listmsg.edit(content=f'This channel is already subscribed to {ytch["name"]}.', embed=None)
                            await ctx.message.delete()
                            return
                with open("data/servers.json", "w") as f:
                    json.dump(servers, f, indent=4)
                ytch = csplit[pagepos][picklist[int(msg.content) - 1]]
                await listmsg.edit(content=f'This channel is now subscribed to: {ytch["name"]}.', embed=None)
                await ctx.message.delete()
                return
            elif msg.content.lower() == 'a':
                with open("data/servers.json") as f:
                    servers = json.load(f)
                await getwebhook(bot, servers, ctx.guild, ctx.channel)
                with open("data/servers.json") as f:
                    servers = json.load(f)
                await msg.delete()
                if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
                    uInput = await subCheck(ctx, bot, listmsg, 1, "Subscribing to all channels.")
                else:
                    uInput = {
                        "success": True,
                        "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
                    }
                if not uInput["success"]:
                    await listmsg.delete()
                    await ctx.message.delete()
                    return
                for subType in uInput["subType"]:
                    for ytch in channels:
                        if ytch not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(ytch)
                with open("data/servers.json", "w") as f:
                    json.dump(servers, f, indent=4)
                await listmsg.edit(content=f'This channel is now subscribed to all Hololive YouTube channels.', embed=None)
                await ctx.message.delete()
                return
            elif msg.content.lower() == 'n' and pagepos < len(csplit) - 1:
                await msg.delete()
                pagepos += 1
                break
            elif msg.content.lower() == 'b' and pagepos > 0:
                await msg.delete()
                pagepos -= 1
                break
            elif msg.content.lower() == 'x':
                await msg.delete()
                await listmsg.delete()
                await ctx.message.delete()
                return
            else:
                await msg.delete()

async def subCustom(ctx: commands.Context, bot: commands.Bot, search: str):
    getChannel = False
    newChannel = False
    channelID = ""
    cInfo = None

    searchMsg = await ctx.send(content="Searching for channel...")

    if "https://www.youtube.com/channel/" in search:
        channelID = search.replace("https://www.youtube.com/channel/", "")
        getChannel = True
    
    if search[0] == "U" and 23 <= len(search) <= 25:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://www.youtube.com/channel/{search}") as r:
                if r.status == 200:
                    cInfo = await channelInfo(channelID)
                    sConfirm = await searchConfirm(ctx, bot, cInfo["name"], searchMsg, f"Subscribe to {cInfo['name']}?", "Subscribe to this channel", "Choose another channel")
                    if sConfirm["success"]:
                        channelID = {
                            "success": True,
                            "channelID": search
                        }
                        getChannel = True
                    elif not sConfirm["success"] and not sConfirm["declined"]:
                        await searchMsg.delete()
                        await ctx.message.delete()
                        return
    
    if not getChannel:
        fandomSearch = await FandomScrape.searchChannel(search)

        if fandomSearch["status"] == "Success":
            sConfirm = await searchConfirm(ctx, bot, fandomSearch["name"], searchMsg, f"Subscribe to {fandomSearch['name']}?", "Subscribe to this channel", "Choose another channel")
            if sConfirm["success"]:
                channelID = await FandomScrape.getChannelURL(fandomSearch["name"])
                cInfo = None
                getChannel = True
            elif not sConfirm["success"] and not sConfirm["declined"]:
                await searchMsg.delete()
                await ctx.message.delete()
                return
        
        if not getChannel or fandomSearch["status"] == "Cannot Match":
            sPick = await searchPrompt(ctx, bot, fandomSearch["results"], searchMsg, "Select a channel to subscribe to:")
            if not sPick["success"]:
                await searchMsg.delete()
                await ctx.message.delete()
                return
            channelID = await FandomScrape.getChannelURL(sPick["name"])
    
    with open("data/channels.json") as f:
        channels = json.load(f)

    if channelID["success"]:
        channelID = channelID["channelID"]
    
    if channelID not in channels:
        if cInfo is None:
            cInfo = await channelInfo(channelID)
        channels[channelID] = {
            "name": cInfo["name"],
            "image": cInfo["image"],
            "milestone": cInfo["roundSubs"],
            "category": "Others"
        }
        newChannel = True
    else:
        cInfo = channels[channelID]
    
    if newChannel:
        with open("data/channels.json", "w", encoding="utf-8") as f:
            json.dump(channels, f, indent=4)
    
    with open("data/servers.json") as f:
        servers = json.load(f)
    
    await getwebhook(bot, servers, ctx.guild, ctx.channel)
    
    if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
        uInput = await subCheck(ctx, bot, searchMsg, 1, cInfo["name"])
    else:
        uInput = {
            "success": True,
            "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
        }
    lastSubbed = False

    if not uInput["success"]:
        await searchMsg.delete()
        await ctx.message.delete()
        return

    for subType in uInput["subType"]:
        if channelID not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(channelID)
        else:
            if len(uInput["subType"]) > 1 and not lastSubbed:
                lastSubbed = True
            else:
                await searchMsg.edit(content=f'This channel is already subscribed to {cInfo["name"]}.', embed=None)
                await ctx.message.delete()
                return

    with open("data/servers.json", "w") as f:
        json.dump(servers, f, indent=4)

    await searchMsg.edit(content=f'This channel is now subscribed to: {cInfo["name"]}.', embed=None)
    await ctx.message.delete()
    return
