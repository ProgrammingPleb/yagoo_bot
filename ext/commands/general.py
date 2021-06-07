import discord
import json
import asyncio
import tweepy
from typing import Union
from discord.ext import commands
from discord_slash.context import SlashContext
from discord_components import Button, ButtonStyle
from ext.share.botVars import allSubTypes
from ..infoscraper import FandomScrape, TwitterScrape
from ..share.botUtils import TwitterUtils, chunks, embedContinue, getAllSubs, msgDelete, fandomTextParse, vtuberSearch
from ..share.dataGrab import getSubType
from ..share.prompts import TwitterPrompts, botError, unsubCheck

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
    # TODO: Add way to search for already subscribed VTubers

    with open("data/servers.json") as f:
        servers = json.load(f)
    with open("data/channels.json") as f:
        channels = json.load(f)
    
    unsubmsg = await ctx.send("Loading subscription list...")

    allCh = await getAllSubs(servers[str(ctx.guild.id)][str(ctx.channel.id)])
    chPages = []
    for section in chunks(allCh, 9):
        chPages.append(section)

    pageNum = 1
    while True:
        dcEmbed = discord.Embed(title="Unsubscribing from Existing Channels", description="YouTube channels this Discord channel is currently subscribed to: ")
        chNum = 1
        chChoice = []
        chChannels = []
        chEmbedText = ""
        for channel in chPages[pageNum - 1]:
            chEmbedText += f"{chNum}. {chPages[pageNum - 1][channel]['name']}\n"
            chChoice.append(str(chNum))
            chChannels.append(channel)
            chNum += 1

        embedNav = ""
        if pageNum > 1:
            embedNav += "B. Go to the previous page\n"
            chChoice.append("b")
        if pageNum < len(chPages):
            embedNav += "N. Go to the next page\n"
            chChoice.append("n")
        embedNav += "A. Unsubscribe from all existing channels\nX. Cancel" # Add "S. Search for a subscribed channel []\n" when search implementation is good
        chChoice += ["s", "a", "x"]

        dcEmbed.add_field(name="Channels", value=chEmbedText, inline=False)
        dcEmbed.add_field(name="Actions", value=embedNav, inline=False)
        await unsubmsg.edit(content=" ", embed=dcEmbed)

        def check(m):
            return m.content.lower() in chChoice and m.author == ctx.author
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await unsubmsg.delete()
            await msgDelete(ctx)
            return
        await msg.delete()
        if msg.content in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            chUnsub = await unsubCheck(ctx, bot, chPages[pageNum - 1][chChannels[int(msg.content) - 1]], unsubmsg)
            
            if not chUnsub["success"]:
                await unsubmsg.delete()
                await msgDelete(ctx)
                return

            subRemove = ""
            with open("data/servers.json") as f:
                servers = json.load(f)
            for subType in chUnsub["subType"]:
                if subType != "twitter":
                    servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].remove(chChannels[int(msg.content) - 1])
                else:
                    servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].remove(channels[chChannels[int(msg.content) - 1]]["twitter"])
                if len(chUnsub["subType"]) > 2:
                    subRemove += f"{subType}, "
                elif len(chUnsub["subType"]) == 2:
                    if "and" in subRemove:
                        subRemove += subType
                    else:
                        subRemove += f"{subType} and "
                else:
                    subRemove = subType
            with open("data/servers.json", "w") as f:
                json.dump(servers, f, indent=4)

            await unsubmsg.edit(content=f"This channel has now been unsubscribed from {chPages[pageNum - 1][chChannels[int(msg.content) - 1]]['name']}. (Types: {subRemove.strip(', ')})", embed=" ")
            await msgDelete(ctx)
            return
        elif msg.content.lower() == "a":
            unsubData = {
                "name": "All Channels",
                "subType": allSubTypes(False)
            }
            unsubTypes = await unsubCheck(ctx, bot, unsubData, unsubmsg)
            
            if not unsubTypes["success"]:
                await unsubmsg.delete()
                await msgDelete(ctx)
                return

            subRemove = ""
            for unsubType in unsubTypes["subType"]:
                servers[str(ctx.guild.id)][str(ctx.channel.id)][unsubType] = []
                if len(unsubTypes["subType"]) > 2:
                    subRemove += f"{unsubType}, "
                elif len(unsubTypes["subType"]) == 2:
                    if "and" in subRemove:
                        subRemove += unsubType
                    else:
                        subRemove += f"{unsubTypes} and "
                else:
                    subRemove = unsubType
            
            with open("data/servers.json", "w") as f:
                json.dump(servers, f, indent=4)

            await unsubmsg.edit(content=f"This channel has now been unsubscribed from all channels. (Types: {subRemove.strip(', ')})", embed=" ")
            return
        elif msg.content.lower() == "b":
            pageNum -= 1
        elif msg.content.lower() == "n":
            pageNum += 1
        elif msg.content.lower() == "S": # Change this back later to lowercase S when can use
            # TODO: Check if current search function can be used here
            continue
        elif msg.content.lower() == "x":
            await unsubmsg.delete()
            await msgDelete(ctx)
            return

async def botSublist(ctx: Union[commands.Context, SlashContext], bot: commands.Bot):
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    with open("data/servers.json") as f:
        servers = json.load(f)
    
    subsmsg = await ctx.send("Loading subscription list...")

    if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
        uInput = await getSubType(ctx, 2, bot, subsmsg)
    else:
        if len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) > 1:
            uInput = {
                "success": True,
                "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"][0]
            }
        else:
            uInput = await getSubType(ctx, 2, bot, subsmsg)

    if not uInput["success"]:
        return
    
    try:
        len(servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]])
    except KeyError:
        await subsmsg.edit(content="There are no subscriptions on this channel.", embed=" ")
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
        await subsmsg.edit(content="There are no subscriptions on this channel.", embed=" ")
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
        await subsmsg.edit(content=" ", embed=subsembed)

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
    retry = True
    infoMsg = None

    while retry:
        fandomName = (await FandomScrape.searchChannel(name, True))["name"]
        fullPage = await FandomScrape.getChannel(fandomName, dataKey="text")
        allSections = await FandomScrape.getSections(fullPage)
        allSData = await FandomScrape.getSectionData(fullPage, allSections)
        infoEmbed, excessParts = await fandomTextParse.parseToEmbed(fandomName, allSData)
        infoEmbed.set_thumbnail(url=await FandomScrape.getThumbnail(fullPage))

        if infoMsg is None:
            infoMsg = await ctx.send(embed=infoEmbed)
        else:
            await infoMsg.edit(embed=infoEmbed)

        if excessParts == None:
            return

        excessChoice = []
        for part in excessParts:
            excessChoice.append(part.lower())
        
        def check(m):
            return m.content.lower() in excessChoice + ['search'] and m.author == ctx.author

        excessLoop = True
        while excessLoop:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                retry = False
                break
            await msg.delete()
            if msg.content.lower() == 'search':
                chChoice = await vtuberSearch(ctx, bot, name, infoMsg, "Get info for", True)
                if chChoice["success"]:
                    name = chChoice["name"]
                    excessLoop = False
                    retry = True
                else:
                    await infoMsg.edit(embed=infoEmbed)
            else:
                for part in excessParts:
                    if msg.content.lower() == part.lower():
                        userReturn = await embedContinue(ctx, bot, infoMsg, part, excessParts[part], fandomName)
                        if userReturn:
                            await infoMsg.edit(embed=infoEmbed)
                            break
                        else:
                            excessLoop = False

# Tasklist:
# Create custom Twitter accounts compatibility layer
# Create disclaimer on core unsubscribe command
# Make Twitter cycle cog get user IDs from custom Twitter compatibility layer
class botTwt:
    async def follow(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, accLink: str):
        twtHandle = ""

        if accLink == "":
            return await ctx.send(embed=await botError(ctx, "No Twitter ID"))
        
        with open("data/twitter.json") as f:
            twtData = json.load(f)
        
        twtHandle = await TwitterUtils.getScreenName(accLink)
        
        try:
            twtUser = await TwitterScrape.getUserDetails(twtHandle)
        except tweepy.NotFound as e:
            return await ctx.send(embed=await botError(ctx, e))

        if "custom" not in twtData:
            twtData["custom"] = {}
        twtEmbed = discord.Embed(title=f"Following {twtUser.name} to this channel", description="Are you sure to subscribe to this Twitter account?")
        twtMsg = await ctx.send(embed=twtEmbed, components=[[Button(label="No", style=ButtonStyle.red), Button(label="Yes", style=ButtonStyle.blue)]])
        
        def check(res):
            return res.user == ctx.message.author and res.channel == ctx.channel
        
        try:
            res = await bot.wait_for('button_click', check=check, timeout=60)
        except asyncio.TimeoutError:
            await twtMsg.delete()
            await msgDelete(ctx)
            return
        if res.component.label == "Yes":
            dbExist = await TwitterUtils.dbExists(twtUser.id_str)
            if not dbExist["status"]:
                twtData = await TwitterUtils.newAccount(twtUser)
            await TwitterUtils.followActions("add", str(ctx.guild.id), str(ctx.channel.id), twtUser.id_str)
            await twtMsg.delete()
            await ctx.send(content=f"This channel is now following @{twtUser.screen_name}'s tweets.")
            await msgDelete(ctx)
            return
        else:
            await twtMsg.delete()
            await msgDelete(ctx)
            return
    
    async def unfollow(ctx: commands.Context, bot: commands.Bot):
        twtMsg = await ctx.send("Loading custom Twitter accounts.")

        with open("data/servers.json") as f:
            servers = json.load(f)
        
        with open("data/twitter.json") as f:
            twitter = json.load(f)
        
        await TwitterPrompts.unfollow(ctx, bot, twtMsg, twitter["custom"], servers)
