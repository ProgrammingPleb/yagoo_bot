import json
import discord
import asyncio
import aiohttp
from discord.ext import commands
from discord_slash.context import SlashContext
from typing import Union
from ..infoscraper import FandomScrape, channelInfo
from ..share.botUtils import chunks, msgDelete, vtuberSearch
from ..share.dataGrab import getwebhook
from ..share.prompts import ctgPicker, subCheck, searchMessage

async def subCategory(ctx: Union[commands.Context, SlashContext], bot: commands.Bot):
    # TODO: Seperate the subscribe code to a function instead

    listmsg = await ctx.send("Loading channels list...")

    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    
    ctgPick = await ctgPicker(ctx, bot, channels, listmsg)

    if ctgPick["search"]:
        srch = await searchMessage(ctx, bot, listmsg)
        await listmsg.delete()
        if not srch["success"]:
            await msgDelete(ctx)
            return
        await subCustom(ctx, bot, srch["search"])
        return
    elif not ctgPick["success"]:
        await listmsg.delete()
        await msgDelete(ctx)
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
        
        await listmsg.edit(content=" ", embed=listembed)

        def check(m):
            return m.content.lower() in pNumList + ['a', 'n', 'b', 's', 'x'] and m.author == ctx.author

        while True:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await listmsg.delete()
                await msgDelete(ctx)
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
                elif servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"] == []:
                    uInput = await subCheck(ctx, bot, listmsg, 1, csplit[pagepos][picklist[int(msg.content) - 1]]["name"])
                else:
                    uInput = {
                        "success": True,
                        "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
                    }
                validSub = False

                if not uInput["success"]:
                    await listmsg.delete()
                    await msgDelete(ctx)
                    return

                for subType in uInput["subType"]:
                    if subType not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
                        servers[str(ctx.guild.id)][str(ctx.channel.id)][subType] = []
                    if subType != "twitter":
                        if picklist[int(msg.content) - 1] not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(picklist[int(msg.content) - 1])
                            validSub = True
                    else:
                        if channels[picklist[int(msg.content) - 1]]["twitter"] not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(channels[picklist[int(msg.content) - 1]]["twitter"])
                            validSub = True
                if not validSub:
                    ytch = csplit[pagepos][picklist[int(msg.content) - 1]]
                    await listmsg.edit(content=f'This channel is already subscribed to {ytch["name"]}.', embed=" ")
                    await msgDelete(ctx)
                    return
                with open("data/servers.json", "w") as f:
                    json.dump(servers, f, indent=4)
                ytch = csplit[pagepos][picklist[int(msg.content) - 1]]
                await listmsg.edit(content=f'This channel is now subscribed to: {ytch["name"]}.', embed=" ")
                await msgDelete(ctx)
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
                elif servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"] == []:
                    uInput = await subCheck(ctx, bot, listmsg, 1, f'{ctgPick["category"]} Channels')
                else:
                    uInput = {
                        "success": True,
                        "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
                    }
                if not uInput["success"]:
                    await listmsg.delete()
                    await msgDelete(ctx)
                    return
                for subType in uInput["subType"]:
                    for ytch in ctgChannels:
                        if subType not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType] = []
                        if subType != "twitter":
                            if ytch not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                                servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(ytch)
                        else:
                            if channels[ytch]["twitter"] not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                                servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(channels[ytch]["twitter"])
                with open("data/servers.json", "w") as f:
                    json.dump(servers, f, indent=4)
                await listmsg.edit(content=f'This channel is now subscribed to all {ctgPick["category"]} YouTube channels.', embed=" ")
                await msgDelete(ctx)
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
                    await msgDelete(ctx)
                    return
                await subCustom(ctx, bot, srch["search"])
                return
            elif msg.content.lower() == 'x':
                await msg.delete()
                await listmsg.delete()
                await msgDelete(ctx)
                return
            else:
                await msg.delete()

async def subCustom(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, search: str):
    newChannel = False
    channelID = ""
    cInfo = None

    searchMsg = await ctx.send(content="Searching for channel...")
    chSearch = await vtuberSearch(ctx, bot, search, searchMsg, "Subscribe to")
    
    if not chSearch["success"]:
        return

    with open("data/channels.json") as f:
        channels = json.load(f)

    if chSearch["success"]:
        channelID = chSearch["channelID"]
    
    if channelID not in channels:
        cInfo = await channelInfo(channelID)
        if not cInfo["success"]:
            await searchMsg.edit(embed=discord.Embed(title="Loading...", description=f"The bot is currently getting info about {chSearch['name']}"))
            cInfo = await channelInfo(channelID, True)
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
    elif servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"] == []:
        uInput = await subCheck(ctx, bot, searchMsg, 1, cInfo["name"])
    else:
        uInput = {
            "success": True,
            "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
        }
    validSub = False

    if not uInput["success"]:
        await searchMsg.delete()
        await msgDelete(ctx)
        return

    for subType in uInput["subType"]:
        if subType not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType] = []
            validSub = True
        if subType != "twitter":
            if channelID not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(channelID)
                validSub = True
        else:
            if channels[channelID]["twitter"] not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(channels[channelID]["twitter"])
                validSub = True
    if not validSub:
        await searchMsg.edit(content=f'This channel is already subscribed to {cInfo["name"]}.', embed=" ")
        await msgDelete(ctx)
        return

    with open("data/servers.json", "w") as f:
        json.dump(servers, f, indent=4)

    await searchMsg.edit(content=f'This channel is now subscribed to: {cInfo["name"]}.', embed=" ")
    await msgDelete(ctx)
    return
