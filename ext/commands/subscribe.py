import json
import discord
import asyncio
import aiohttp
from discord.ext import commands
from ..infoscraper import FandomScrape, channelInfo
from ..share.botUtils import chunks
from ..share.dataGrab import getwebhook
from ..share.prompts import ctgPicker, subCheck, searchConfirm, searchPrompt, searchMessage

async def subCategory(ctx: commands.Context, bot: commands.Bot):
    listmsg = await ctx.send("Loading channels list...")

    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    
    ctgPick = await ctgPicker(ctx, bot, channels, listmsg)

    if ctgPick["search"]:
        srch = await searchMessage(ctx, bot, listmsg)
        await listmsg.delete()
        if not srch["success"]:
            await ctx.message.delete()
            return
        await subCustom(ctx, bot, srch["search"])
        return
    elif not ctgPick["success"]:
        await listmsg.delete()
        await ctx.message.delete()
        return
    
    ctgChannels = {}
    for channel in channels:
        if channels[channel]["category"] == ctgPick["category"]:
            ctgChannels[channel] = channels[channel]

    csplit = []
    for split in chunks(ctgChannels, 9):
        csplit.append(split)
    pagepos = 0
    
    while True:
        listembed = discord.Embed(title="Subscribing to a Channel", description="Pick a number/letter corresponding to the channel/action.\n"
                                                                                "If the VTuber is not in this list, search the VTuber to add it to the bot's database.")

        picknum = 1
        pickstr = ""
        picklist = []
        pNumList = []
        for split in csplit[pagepos]:
            ytch = csplit[pagepos][split]
            pickstr += f'{picknum}. {ytch["name"]}\n'
            picklist.append(split)
            pNumList.append(str(picknum))
            picknum += 1
        listembed.add_field(name="Channels", value=pickstr.strip())
        if len(csplit) == 1:
            listembed.add_field(name="Actions", value=f'A. Subscribe to all channels\nS. Search for a VTuber\nX. Cancel')
        elif pagepos == 0:
            listembed.add_field(name="Actions", value=f'A. Subscribe to all channels\nN. Go to next page\nS. Search for a VTuber\nX. Cancel')
        elif pagepos == len(csplit) - 1:
            listembed.add_field(name="Actions", value=f'A. Subscribe to all channels\nB. Go to previous page\nS. Search for a VTuber\nX. Cancel')
        else:
            listembed.add_field(name="Actions", value=f'A. Subscribe to all channels\nN. Go to next page\nB. Go to previous page\nS. Search for a VTuber\nX. Cancel')
        
        await listmsg.edit(content=None, embed=listembed)

        def check(m):
            return m.content.lower() in pNumList + ['a', 'n', 'b', 's', 'x'] and m.author == ctx.author

        while True:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await listmsg.delete()
                await ctx.message.delete()
                return
            if msg.content in pNumList:
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
                    for ytch in ctgChannels:
                        if ytch not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(ytch)
                with open("data/servers.json", "w") as f:
                    json.dump(servers, f, indent=4)
                await listmsg.edit(content=f'This channel is now subscribed to all {ctgPick["category"]} YouTube channels.', embed=None)
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
            elif msg.content.lower() == 's':
                await msg.delete()
                srch = await searchMessage(ctx, bot, listmsg)
                await listmsg.delete()
                if not srch["success"]:
                    await ctx.message.delete()
                    return
                await subCustom(ctx, bot, srch["search"])
                return
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
        for part in search.split("/"):
            if 23 <= len(part) <= 25:
                if part[0] == "U":
                    channelID = part
                    getChannel = True
    
    if 23 <= len(search) <= 25:
        if search[0] == "U":
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
            "category": await FandomScrape.getAffiliate(cInfo["name"])
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
