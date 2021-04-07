import discord
import json
import asyncio
from typing import Union
from discord.ext import commands
from discord_slash.context import SlashContext
from ..infoscraper import FandomScrape
from ..share.botUtils import embedContinue, msgDelete, fandomTextParse
from ..share.dataGrab import getwebhook, getSubType
from ..share.prompts import subCheck

async def botHelp():
    hembed = discord.Embed(title="Yagoo Bot Commands")
    hembed.description = "Currently the bot only has a small number of commands, as it is still in development!\n" \
                         "New stream notifications will be posted on a 3 minute interval, thus any new notifications " \
                         "will not come immediately after subscribing.\n" \
                         "Currently all the commands (except for `y!help` and `y!info`) require the user to have either the `Administrator` or `Manage Webhook` permission in the channel or server.\n" \
                         "Anything in angle brackets `<>` are required, leaving them will result in an error." \
                         "Meanwhile, anything in square brackets `[]` are optional, so leaving them will also make the command work."
    
    hembed.add_field(name="Commands",
                     value="**y!sub** [VTuber Name] (Alias: subscribe)\n"
                           "Brings up a list of channels to subscribe to.\n"
                           "Add a non-Hololive VTuber's name to the command to opt in to their notifications.\n\n"
                           "**y!unsub** (Alias: unsubscribe)\n"
                           "Brings up a list of channels to unsubscribe to.\n\n"
                           "**y!sublist** (Alias: subs, subslist)\n"
                           "Brings up a list of channels that the current chat channel has subscribed to.\n\n"
                           "**y!subdefault** (Alias: subDefault)\n"
                           "Set's the default subscription type for the channel.\n\n"
                           "**y!info** <VTuber Name> (Alias: getinfo)\n"
                           "Gets information about a VTuber.",
                     inline=False)
    
    hembed.add_field(name="Issues/Suggestions?",
                     value="If you run into any problems with/have any suggestions for the bot, then feel free to join the [support server](https://discord.gg/GJd6sdNjeQ) and drop a message there.",
                     inline=False)

    return hembed

async def botUnsub(ctx: Union[commands.Context, SlashContext], bot: commands.Bot):
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
        await msgDelete(ctx)
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
                await msgDelete(ctx)
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
                    await msgDelete(ctx)
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
                    await msgDelete(ctx)
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
                    await msgDelete(ctx)
                    return
                else:
                    await msg.delete()

async def botSublist(ctx: Union[commands.Context, SlashContext], bot: commands.Bot):
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    with open("data/servers.json") as f:
        servers = json.load(f)
    
    subsmsg = await ctx.send("Loading subscription list...")

    if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
        uInput = await getSubType(ctx, 2, bot, subsmsg)
    else:
        if not len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) > 1:
            uInput = {
                "success": True,
                "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"][0]
            }
        else:
            uInput = {
                "success": True,
                "subType": "livestream"
            }

    if not uInput["success"]:
        return
    
    try:
        len(servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]])
    except KeyError:
        await subsmsg.edit(content="There are no subscriptions on this channel.", embed=None)
        return

    multi = False
    sublist = []
    templist = []
    if len(servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]) > 10:
        for sub in servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]:
            if len(templist) < 10:
                templist.append(sub)
            else:
                sublist.append(templist)
                templist = [sub]
        sublist.append(templist)
        multi = True
    elif len(servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]) > 0 and len(servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]) < 11:
        for sub in servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]:
            sublist.append(sub)
    else:
        await subsmsg.edit(content="There are no subscriptions on this channel.", embed=None)
        return
    
    pagepos = 0
    realnum = 1
    while True:
        dispstring = ""
        if multi:
            subProc = sublist[pagepos]
            for sub in subProc:
                ytch = channels[sub]
                dispstring += f'{realnum}. {ytch["name"]}\n'
                realnum += 1
            if pagepos == 0:
                dispstring += f'\nN. Go to next page\nX. Remove this message'
            elif pagepos == len(sublist) - 1:
                dispstring += f'\nB. Go to previous page\nX. Remove this message'
            else:
                dispstring += f'\nN. Go to next page\nB. Go to previous page\nX. Remove this message'
        else:
            subProc = sublist
            for sub in sublist:
                ytch = channels[sub]
                dispstring += f'{realnum}. {ytch["name"]}\n'
                realnum += 1
            dispstring += f'\nX. Remove this message'
        
        subsembed = discord.Embed(title="Currently subscribed channels:", description=dispstring)
        await subsmsg.edit(content=None, embed=subsembed)

        def check(m):
            return m.content.lower() in ['n', 'b', 'x'] and m.author == ctx.author

        while True:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                return
            else:
                if msg.content.lower() == 'x':
                    await msg.delete()
                    await subsmsg.delete()
                    await msgDelete(ctx)
                    return
                if multi:
                    if msg.content.lower() == 'n' and pagepos < len(sublist) - 1:
                        await msg.delete()
                        pagepos += 1
                        break
                    elif msg.content.lower() == 'b' and pagepos > 0:
                        await msg.delete()
                        pagepos -= 1
                        realnum -= 20
                        break
                else:
                    await msg.delete()

async def botGetInfo(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, name: str):
    fandomName = (await FandomScrape.searchChannel(name, True))["name"]
    fullPage = await FandomScrape.getChannel(fandomName, dataKey="text")
    allSections = await FandomScrape.getSections(fullPage)
    allSData = await FandomScrape.getSectionData(fullPage, allSections)
    infoEmbed, excessParts = await fandomTextParse.parseToEmbed(fandomName, allSData)
    infoEmbed.set_thumbnail(url=await FandomScrape.getThumbnail(fullPage))

    infoMsg = await ctx.send(embed=infoEmbed)

    if excessParts == None:
        return

    excessChoice = []
    for part in excessParts:
        excessChoice.append(part.lower())
    
    def check(m):
        return m.content.lower() in excessChoice and m.author == ctx.author

    excessLoop = True
    while excessLoop:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            break
        await msg.delete()
        for part in excessParts:
            if msg.content.lower() == part.lower():
                userReturn = await embedContinue(ctx, bot, infoMsg, part, excessParts[part], fandomName)
                if userReturn:
                    await infoMsg.edit(embed=infoEmbed)
                    break
                else:
                    excessLoop = False
