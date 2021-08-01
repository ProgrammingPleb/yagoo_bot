import discord
import mysql.connector
from discord.ext import commands
from discord_slash.context import SlashContext
from discord_slash.model import ButtonStyle
from typing import Union
from ..infoscraper import FandomScrape
from ..share.botUtils import msgDelete
from ..share.botVars import allSubTypes
from ..share.dataUtils import botdb, dbTools
from ..share.prompts import generalPrompts, pageNav, subPrompts, subPrompts, unsubPrompts

async def subCategory(ctx: Union[commands.Context, SlashContext], bot: commands.Bot):
    """
    Subscription prompt that uses a category and channel based selection.
    
    Arguments
    ---
    ctx: Context from the executed command.
    bot: The Discord bot.
    """
    db = await botdb.getDB()
    listmsg = await ctx.send("Loading channels list...")
    
    channels = await botdb.getAllData("channels", ("id", "category"), keyDict="id", db=db)
    ctgPick = await subPrompts.ctgPicker(ctx, bot, channels, listmsg)
    
    if not ctgPick["status"]:
        await listmsg.delete()
        await ctx.message.delete()
        return
    
    server = await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), ("subDefault", "livestream", "milestone", "premiere", "twitter"), db)
    if ctgPick["all"]:
        subResult = await subUtils.subAll(ctx, bot, listmsg, server, str(ctx.channel.id), db)
        chName = None
    elif ctgPick["search"]:
        result = await subUtils.channelSearch(ctx, bot, listmsg)
        if result["status"]:
            chData = await botdb.getData(result["channelID"], "id", ("name", ), "channels", db)
            subResult = await subUtils.subOne(ctx, bot, listmsg, server, str(ctx.channel.id), result["channelID"], chData["name"], db)
            chName = chData["name"]
        else:
            subResult = {
                "status": False
            }
    else:
        channels = await botdb.getAllData("channels", ("id", "name"), ctgPick["category"], "category", keyDict="id", db=db)
        result = await subPrompts.channelPick.prompt(ctx, bot, listmsg, channels, ctgPick["category"])
        if result["status"]:
            if result["other"]:
                subResult = await subUtils.subAll(ctx, bot, listmsg, server, str(ctx.channel.id), db, ctgPick["category"])
                chName = f"all {ctgPick['category']} VTubers"
            elif result["search"]:
                result = await subUtils.channelSearch(ctx, bot, listmsg)
                if result["status"]:
                    chData = await botdb.getData(result["channelID"], "id", ("name", ), "channels", db)
                    subResult = await subUtils.subOne(ctx, bot, listmsg, server, str(ctx.channel.id), result["channelID"], chData["name"], db)
                    chName = chData["name"]
                else:
                    subResult = {
                        "status": False
                    }
            else:
                subResult = await subUtils.subOne(ctx, bot, listmsg, server, str(ctx.channel.id), result["item"]["id"], result["item"]["name"], db)
                chName = result["item"]["name"]
    if subResult["status"]:
        await subPrompts.displaySubbed(listmsg, ctgPick["all"], ctgPick["category"], subResult["subbed"], chName)
        await msgDelete(ctx)
        return
    await listmsg.delete()
    await msgDelete(ctx)

async def subCustom(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, search: str):
    """
    Subscribes to a VTuber with the channel name provided to the user.
    
    Arguments
    ---
    ctx: Context from the executed command.
    bot: The Discord bot.
    search: The name of the channel to search for.
    """
    db = await botdb.getDB()
    searchMsg = await ctx.send("Loading channels list...")
    
    result = await subUtils.channelSearch(ctx, bot, searchMsg, search)
    if result["status"]:
        server = await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), tuple(["subDefault"] +  allSubTypes(False)), db)
        subResult = await subUtils.subOne(ctx, bot, searchMsg, server, str(ctx.channel.id), result["channelID"], result["channelName"], db)
        if subResult["status"]:
            await subPrompts.displaySubbed(searchMsg, False, None, subResult["subbed"], result["channelName"])
            await msgDelete(ctx)
            return
    await searchMsg.delete()
    await msgDelete(ctx)

async def unsubChannel(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, channel: str = None):
    """
    Unsubscribes from a VTuber. (bypasses a prompt if a channel is given)
    
    Arguments
    ---
    ctx: Context from the executed command.
    bot: The Discord bot.
    channel: The search term for the VTuber.
    """
    db = await botdb.getDB()
    listMsg = await ctx.send("Loading channel subscriptions...")
    server = await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), tuple(allSubTypes(False)), db)
    
    subList = await unsubUtils.parseToSubTypes(server, db)
    if not subList["subbed"]:
        raise ValueError("No Subscriptions")
    if not channel:
        subPages = await unsubUtils.parseToPages(subList)
        result = await pageNav.search.prompt(ctx, bot, listMsg,
                                             subPages, "Unsubscribing from a Channel",
                                             "Search for a VTuber", "Unsubscribe from all VTubers",
                                             "removeAll", ButtonStyle.red, "Choose the VTuber to be unsubscribed from:")
    else:
        wikiName = await subUtils.channelSearch(ctx, bot, listMsg, channel, "unsubscribe")
        if wikiName["status"]:
            result = {
                "status": True, 
                "other": False, 
                "search": False, 
                "item": {
                    "name": wikiName["channelName"],
                    "id": wikiName["channelID"]
                }
            }
        else:
            result = {
                "status": False
            }
    
    if result["status"]:
        if result["other"]:
            currentSubs = {}
            for subType in allSubTypes(False):
                currentSubs[subType] = True
            unsubResult = await unsubPrompts.removePrompt.prompt(ctx, bot, listMsg, "all VTubers", currentSubs)
            if not unsubResult["status"]:
                await listMsg.delete()
                await msgDelete(ctx)
                return
            result = await unsubUtils.unsubAll(str(ctx.channel.id), unsubResult["unsubbed"], db)      
        elif result["search"]:
            searchResult = await subUtils.channelSearch(ctx, bot, listMsg, action = "unsubscribe")
            if not searchResult["status"]:
                await listMsg.delete()
                await msgDelete(ctx)
                return
            unsubResult = await unsubPrompts.removePrompt.prompt(ctx, bot, listMsg, searchResult["channelName"], subList["channels"][searchResult["channelID"]]["subTypes"])
            if not unsubResult["status"]:
                await listMsg.delete()
                await msgDelete(ctx)
                return
            result = await unsubUtils.unsubOne(server, str(ctx.channel.id), searchResult["channelID"], unsubResult["unsubbed"], db)
        else:
            unsubResult = await unsubPrompts.removePrompt.prompt(ctx, bot, listMsg, result["item"]["name"], subList["channels"][result["item"]["id"]]["subTypes"])
            if not unsubResult["status"]:
                await listMsg.delete()
                await msgDelete(ctx)
                return
            result = await unsubUtils.unsubOne(server, str(ctx.channel.id), result["item"]["id"], unsubResult["unsubbed"], db)
        await unsubPrompts.displayResult(listMsg, result["name"], result["subTypes"])
        await msgDelete(ctx)
        return
    await listMsg.delete()
    await msgDelete(ctx)

async def sublistDisplay(ctx: Union[commands.Context, SlashContext], bot: commands.Bot):
    """
    Show the user about the current subscriptions for the channel.
    
    Arguments
    ---
    ctx: Context from the executed command.
    bot: The Discord bot.
    """
    db = await botdb.getDB()
    listMsg = await ctx.send("Loading channel subscriptions...")
    server = await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), tuple(allSubTypes(False)), db)
    
    subList = await unsubUtils.parseToSubTypes(server, db)
    pages = await subPrompts.sublistDisplay.parseToPages(subList)
    await subPrompts.sublistDisplay.prompt(ctx, bot, listMsg, pages, subList)
    await msgDelete(ctx)
    return

async def defaultSubtype(ctx: Union[commands.Context, SlashContext], bot: commands.Bot):
    db = await botdb.getDB()
    subMsg = await ctx.send("Loading channel subscription defaults...")
    server = await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), ("subDefault",), db)
    
    subTypes = {}
    for subType in allSubTypes(False):
        subTypes[subType] = False
    if not (server["subDefault"] is None or server["subDefault"] == ""):
        for subType in await botdb.listConvert(server["subDefault"]):
            subTypes[subType] = True
    
    result = await subPrompts.subTypes.prompt(ctx, bot, subMsg,
                                              "Default Channel Subscription Types",
                                              "Pick the subscription types for this channel to subscribe to by default.",
                                              "Confirm", "confirm", subTypes, True)
    if result["status"]:
        subDefault = []
        for subType in result["subTypes"]:
            if result["subTypes"][subType]:
                subDefault.append(subType)
        await botdb.addData((str(ctx.channel.id), await botdb.listConvert(subDefault)), ("channel", "subDefault"), "servers", db)
        
        defaultSubs = ""
        if subDefault == []:
            defaultSubs = "No Defaults"
            promptStatus = "Subscription commands will now ask for subscription types first."
        else:
            for sub in subDefault:
                defaultSubs += f"{sub}, "
            promptStatus = "Subscription commands will now follow the channel's defaults."
        embed = discord.Embed(title="Successfully Set Channel Defaults!",
                              description=f"This channel's defaults are now set.\n{promptStatus}",
                              color=discord.Colour.green())
        embed.add_field(name="Default Subscriptions", value=defaultSubs.strip(", "), inline=False)
        await subMsg.edit(content=" ", embed=embed, components=[])
        await msgDelete(ctx)
        return
    await subMsg.delete()
    await msgDelete(ctx)

class subUtils:
    async def checkDefault(data: dict):
        """
        Checks if the channel has a subscription default.
        
        Arguments
        ---
        data: The channel's data containing a `subDefault` key.
        
        Returns
        ---
        The channel's subscription defaults as a `list`, `None` if there is no default set.
        """
        if data is None:
            return None
        
        subDefault = await botdb.listConvert(data["subDefault"])
        if subDefault == "" or subDefault is None:
            return None
        else:
            return subDefault
    
    async def channelSearch(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, channel: str = None, action: str = "subscribe"):
        """
        Searches for a channel with input from the user.
        
        Arguments
        ---
        ctx: Context from the executed command.
        bot: The Discord bot.
        msg: The message that will be used for the prompt.
        channel: The name of the channel if already provided by the user.
        
        Result
        ---
        A `dict` with:
        - status: `True` if the user successfully searches for a VTuber.
        - channelID: The channel ID of the VTuber channel.
        - channelName: The name of the channel.
        """
        if channel is None:
            result = await generalPrompts.cancel(ctx, bot, msg, "Searching for a VTuber", "Enter the name of the VTuber you want to search for.")
        else:
            result = {
                "status": True,
                "res": channel
            }
        
        if result["status"]:
            wikiName = await FandomScrape.searchChannel(result["res"])
            
            while True:
                if wikiName["status"] == "Cannot Match":
                    wikiName = await subPrompts.searchPick(ctx, bot, msg, result["res"], wikiName["results"])
                    if not wikiName["status"]:
                        return {
                            "status": False
                        }

                uConfirm = await subPrompts.vtuberConfirm.prompt(ctx, bot, msg, wikiName["name"], action)
                if uConfirm["status"]:
                    if uConfirm["action"] == "confirm":
                        break
                    else:
                        wikiName["status"] = "Cannot Match"
                else:
                    return {
                        "status": False
                    }
            
            channelId = await FandomScrape.getChannelURL(wikiName["name"])
            if channelId["success"]:
                return {
                    "status": True,
                    "channelID": channelId["channelID"],
                    "channelName": wikiName["name"]
                }
        return {
            "status": False
        }
    
    async def subOne(ctx: Union[commands.Context, SlashContext],
                     bot: commands.Bot,
                     msg: discord.Message,
                     server: dict,
                     channelId: str,
                     ytChID: str,
                     ytChName: str,
                     db: mysql.connector.MySQLConnection):
        """
        Subscribes to one channel with the specified channel ID.
        
        Arguments
        ---
        ctx: Context from the executed command.
        bot: The Discord bot.
        msg: The message that will be used as a prompt.
        server: The server as a `dict` containing `subDefault` and other subscription types.
        channelId: The channel ID of the current Discord channel.
        db: An existing MySQL connection to reduce unnecessary connections.
        
        Returns
        ---
        A `dict` with:
        - status: `True` if the subscription command was executed successfully.
        - subbed: A list containing the subscribed subscription types.
        """
        subDefault = await subUtils.checkDefault(server)
        subbed = []
        
        if subDefault == [''] or subDefault is None:
            result = await subPrompts.subTypes.prompt(ctx, bot, msg, f"Subscribing to {ytChName}",
                                                      "Pick the notifications to be posted to this channel.\n"
                                                      "(This prompt can be bypassed by setting a default subscription type "
                                                      "using the `subDefault` command)")
            if not result["status"]:
                return {
                    "status": False
                }
            subDefault = []
            for subType in result["subTypes"]:
                if result["subTypes"][subType]:
                    subDefault.append(subType)
        for subType in subDefault:
            stData = await botdb.listConvert(server[subType])
            if not stData:
                stData = []
            if subType == "twitter":
                twitter = (await botdb.getData(ytChID, "id", ("twitter", ), "channels", db))["twitter"]
                if twitter is not None:
                    if twitter not in stData:
                        stData.append(twitter)
                        await botdb.addData((channelId, await botdb.listConvert(stData)), ("channel", subType), "servers", db)
                        subbed.append(subType)
            else:
                if ytChID not in stData:
                    stData.append(ytChID)
                    await botdb.addData((channelId, await botdb.listConvert(stData)), ("channel", subType), "servers", db)
                    subbed.append(subType)
        return {
            "status": True,
            "name": (await botdb.getData(ytChID, "id", ("name", ), "channels", db))["name"],
            "subbed": subbed
        }
    
    async def subAll(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, server: dict, channelId: str, db: mysql.connector.MySQLConnection, category: str = None):
        """
        Subscribes to all channels (in a category if specified, every channel if otherwise).
        
        Arguments
        ---
        ctx: Context from the executed command.
        bot: The Discord bot.
        msg: The message that will be used for prompts.
        server: The server as a `dict` containing `subDefault` and other subscription types.
        channelId: The channel ID of the current Discord channel.
        db: An existing MySQL connection to reduce unnecessary connections.
        category: The category filter for subscribing to channels within the category.
        
        Returns
        ---
        A `dict` with:
        - status: `True` if the subscription command was executed successfully.
        - subbed: A list containing the subscribed subscription types.
        """
        channel = await botdb.getAllData("channels", ("id", "twitter"), category, "category", db=db)
        subDefault = await subUtils.checkDefault(server)
        twitter = []
        channels = []
        
        for ch in channel:
            channels.append(ch["id"])
            twitter.append(ch["twitter"])
        
        if category is None:
            category = ""
        else:
            category += " "
        
        if subDefault == [''] or subDefault is None:
            subDefault = []
            result = await subPrompts.subTypes.prompt(ctx, bot, msg, f"Subscribing to all {category}VTubers",
                                                      "Pick the notifications to be posted to this channel.\n"
                                                      "(This prompt can be bypassed by setting a default subscription type "
                                                      "using the `subDefault` command)")
            if result:
                for subType in result["subTypes"]:
                    if result["subTypes"][subType]:
                        subDefault.append(subType)
        for subType in subDefault:
            serverType = await botdb.listConvert(server[subType])
            if serverType is None:
                serverType = []
            if subType != "twitter":
                newData = list(set(serverType) | set(channels))
            else:
                newData = list(set(serverType) | set(twitter))
            await botdb.addData((channelId, await botdb.listConvert(newData)), ("channel", subType), "servers", db)
        return {
            "status": True,
            "subbed": subDefault
        }

class unsubUtils:
    async def parseToPages(server: dict):
        """
        Parses the current channel's subscriptions into a page format to be used in `pageNav.message()`.
        
        Arguments
        ---
        server: The Discord channel's subscription data as a `dict`, obtained from `parseToSubTypes`.
        db: A MySQL connection to the database to reduce unnecessary connections.
        
        Returns
        ---
        A `list` following the pages format specified in `pageNav.message()`.
        """
        result = []
        text = ""
        entries = []
        ids = []
        names = []
        pos = 1
        
        for channel in server["channels"]:
            text += f"{pos}. {server['channels'][channel]['name']}\n"
            entries.append(str(pos))
            ids.append(channel)
            names.append(server['channels'][channel]['name'])
            pos += 1
            if pos == 10:
                result.append({"text": text.strip(), "entries": entries, "ids": ids, "names": names})
                text = ""
                entries = []
                ids = []
                names = []
                pos = 1
        if pos > 1:
            result.append({"text": text.strip(), "entries": entries, "ids": ids, "names": names})
        return result
    
    async def parseToSubTypes(server: dict, db: mysql.connector.CMySQLConnection):
        """
        Parses the current channel's subscriptions to subscription indicators.
        
        Arguments
        ---
        server: The Discord channel's data as a `dict` containing all the subscription types for it.
        db: A MySQL connection to the database to reduce unnecessary connections.
        
        Returns
        ---
        A `dict` with:
        - subbed: A `list` containing the IDs of the subscribed channels.
        - channels: A `dict` with channels containing `name` and `subTypes` (current subscription types as sub-keys).
        """
        channels = await botdb.getAllData("channels", ("id", "name", "twitter"), db=db)
        
        subTypes = allSubTypes(False)
        subbed = []
        subbedTypes = {}
        cTypeSubbed = {}
        for subType in subTypes:
            temp = await botdb.listConvert(server[subType])
            if temp is None:
                temp = []
            cTypeSubbed[subType] = temp
        
        for channel in channels:
            if channel["id"] not in subbed:
                subbed.append(channel["id"])
                subbedTypes[channel["id"]] = {
                    "name": channel["name"],
                    "subTypes": {}
                }
                for subType in subTypes:
                    if channel["id"] in cTypeSubbed[subType] or channel["twitter"] in cTypeSubbed[subType]:
                        if subType != "twitter":
                            subbedTypes[channel["id"]]["subTypes"][subType] = channel["id"] in cTypeSubbed[subType]
                        else:
                            subbedTypes[channel["id"]]["subTypes"][subType] = channel["twitter"] in cTypeSubbed[subType]
        return {
            "subbed": subbed,
            "channels": subbedTypes
        }
    
    async def unsubOne(server: dict, serverID: str, channelID: str, subTypes: list, db: mysql.connector.CMySQLConnection):
        """
        Unsubscribe from one VTuber channel from the Discord channel.
        
        Arguments
        ---
        server: The current channel's subscriptions as a `dict`. (subscription types as keys)
        serverID: The Discord channel's ID.
        channelID: The VTuber channel's ID.
        subTypes: The subscription types to unsubscribe from as a `list`.
        db: A MySQL connection to reduce the amount of unnecessary connections.
        
        Returns
        ---
        A `dict` with:
        - name: The name of the VTuber being unsubscribed from.
        - subTypes: The subscription types given in the respective argument.
        """
        for subType in subTypes:
            typeSubs = await botdb.listConvert(server[subType])
            if subType == "twitter":
                twitter = await botdb.getData(channelID, "channel", ("twitter",), "channels", db)
                if twitter in typeSubs:
                    typeSubs.remove(twitter)
                    await botdb.addData((serverID, await botdb.listConvert(typeSubs)), ("channel", subType), "servers", db)
            else:
                typeSubs.remove(channelID)
                await botdb.addData((serverID, await botdb.listConvert(typeSubs)), ("channel", subType), "servers", db)
        return {
            "name": (await botdb.getData(channelID, "id", ("name",), "channels", db))["name"],
            "subTypes": subTypes
        }
    
    async def unsubAll(serverID: str, subTypes: list, db: mysql.connector.CMySQLConnection):
        """
        Unsubscribe from every VTuber channel from the Discord channel.
        
        Arguments
        ---
        serverID: The Discord channel's ID.
        subTypes: The subscription types to unsubscribe from as a `list`.
        db: A MySQL connection to reduce the amount of unnecessary connections.
        
        Returns
        ---
        A `dict` with:
        - name: The name of the VTuber being unsubscribed from. (`all Vtubers`)
        - subTypes: The subscription types given in the respective argument.
        """
        for subType in subTypes:
            await botdb.deleteCell(subType, serverID, "channel", "servers", db)
        return {
            "name": "all VTubers",
            "subTypes": subTypes
        }
