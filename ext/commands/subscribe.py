import discord
import mysql.connector
from discord.ext import commands
from discord_slash.context import SlashContext
from discord_slash.model import ButtonStyle
from typing import Union
from ..infoscraper import FandomScrape, channelInfo
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
            subResult = await subUtils.subOne(ctx, bot, listmsg, server, str(ctx.channel.id), result["channelID"], result["channelName"], db)
            chName = result["channelName"]
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
                    subResult = await subUtils.subOne(ctx, bot, listmsg, server, str(ctx.channel.id), result["channelID"], result["channelName"], db)
                    chName = result["channelName"]
                else:
                    subResult = {
                        "status": False
                    }
            else:
                subResult = await subUtils.subOne(ctx, bot, listmsg, server, str(ctx.channel.id), result["item"]["id"], result["item"]["name"], db)
                chName = subResult["name"]
        else:
            subResult = {
                "status": False
            }
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
            await subPrompts.displaySubbed(searchMsg, False, None, subResult["subbed"], subResult["name"])
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
                                             "removeAll", ButtonStyle.red, "Choose the VTuber to be unsubscribed from:",
                                             True, 1, 25)
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
            unsubResult = await unsubPrompts.removePrompt.prompt(ctx, bot, listMsg, ["channelAllUnsub"], ["all VTubers"], currentSubs)
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
            unsubResult = await unsubPrompts.removePrompt.prompt(ctx, bot, listMsg, searchResult["channelID"], searchResult["channelName"], subList["channels"])
            if not unsubResult["status"]:
                await listMsg.delete()
                await msgDelete(ctx)
                return
            result = await unsubUtils.unsubOne(server, str(ctx.channel.id), searchResult["channelID"], searchResult["channelName"], unsubResult["unsubbed"], db)
        else:
            unsubResult = await unsubPrompts.removePrompt.prompt(ctx, bot, listMsg, result["item"]["id"], result["item"]["name"], subList["channels"])
            if not unsubResult["status"]:
                await listMsg.delete()
                await msgDelete(ctx)
                return
            result = await unsubUtils.unsubOne(server, str(ctx.channel.id), result["item"]["id"], result["item"]["name"], unsubResult["unsubbed"], db)
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
    if len(pages) == 0:
        raise ValueError("No Subscriptions")
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
    
    async def addChannel(channelID: str, channelName: str, returnType: tuple, db: mysql.connector.MySQLConnection):
        """
        Gets the YouTube channel from the ID in the database and creates a new listing if it doesn't exist.
        
        Arguments
        ---
        channelID: The channel ID of the YouTube channel.
        channelName: The Fandom wiki name of the YouTube channel.
        returnType: The type of data to return.
        db: An existing MySQL connection to reduce unneccessary connections.
        
        Returns
        ---
        A `dict` of the channel's data.
        """
        scrape: dict = await channelInfo(channelID, True)
        columns = ("id", "name", "image", "milestone", "category", "twitter")
        data = []
        for column in columns:
            if column == "milestone":
                data.append(scrape["roundSubs"])
            elif column == "twitter" and "twitter" not in scrape:
                data.append(None)
            elif column == "category":
                data.append(await FandomScrape.getAffiliate(channelName))
            else:
                data.append(scrape[column])
        await botdb.addData(tuple(data), columns, "channels", db)
        chData = await botdb.getData(channelID, "id", returnType, "channels", db)
        
        return chData
    
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
                db = await botdb.getDB()
                if not await botdb.checkIfExists(channelId["channelID"], "id", "channels", db):
                    embed = discord.Embed(title="Getting Channel Data...", description="This channel is new in the database.\nPlease wait while we're getting the channel's info.")
                    await msg.edit(content=" ", embed=embed, components=[])
                    chData = await subUtils.addChannel(channelId["channelID"], wikiName["name"], ("id", "name"), db)
                else:
                    chData = await botdb.getData(channelId["channelID"], "id", ("id", "name"), "channels", db)
                return {
                    "status": True,
                    "channelID": [chData["id"]],
                    "channelName": [chData["name"]]
                }
        return {
            "status": False
        }
    
    async def subOne(ctx: Union[commands.Context, SlashContext],
                     bot: commands.Bot,
                     msg: discord.Message,
                     server: dict,
                     channelId: str,
                     ytChID: list,
                     chNames: list,
                     db: mysql.connector.MySQLConnection):
        """
        Subscribes to one/multiple channel(s) with the specified channel ID(s).
        
        Arguments
        ---
        ctx: Context from the executed command.
        bot: The Discord bot.
        msg: The message that will be used as a prompt.
        server: The server as a `dict` containing `subDefault` and other subscription types.
        channelId: The channel ID of the current Discord channel.
        chNames: 
        db: An existing MySQL connection to reduce unnecessary connections.
        
        Returns
        ---
        A `dict` with:
        - status: `True` if the subscription command was executed successfully.
        - subbed: A list containing the subscribed subscription types.
        """
        subDefault = await subUtils.checkDefault(server)
        subbed = []
        
        if len(chNames) > 1:
            ytChName = "Multiple Channels"
        else:
            ytChName = chNames[0]
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
        for channel in ytChID:
            for subType in subDefault:
                stData = await botdb.listConvert(server[subType])
                if not stData:
                    stData = []
                if subType == "twitter":
                    twitter = (await botdb.getData(channel, "id", ("twitter", ), "channels", db))["twitter"]
                    if twitter is not None:
                        if twitter not in stData:
                            stData.append(twitter)
                            server[subType] = await botdb.listConvert(stData)
                            await botdb.addData((channelId, await botdb.listConvert(stData)), ("channel", subType), "servers", db)
                            if subType not in subbed:
                                subbed.append(subType)
                else:
                    if channel not in stData:
                        stData.append(channel)
                        server[subType] = await botdb.listConvert(stData)
                        await botdb.addData((channelId, await botdb.listConvert(stData)), ("channel", subType), "servers", db)
                        if subType not in subbed:
                            subbed.append(subType)
        if len(chNames) <= 5:
            channels = ""
            for channel in ytChID:
                channels += (await botdb.getData(channel, "id", ("name", ), "channels", db))["name"] + ", "
            channels = channels[:-2]
        else:
            channels = f"{len(chNames)} channels"
        return {
            "status": True,
            "name": channels,
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
            if ch["id"]:
                channels.append(ch["id"])
            if ch["twitter"]:
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
        
        for channel in server["channels"]:
            if 25 < len(server["channels"][channel]["name"]) > 22:
                name = (server["channels"][channel]["name"])[:22] + "..."
            else:
                name = server["channels"][channel]["name"]
            result.append({"name": name, "id": channel})
        
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
                subStatus = False
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
                        subStatus = True
                if subStatus:
                    subbed.append(channel["id"])
                else:
                    subbedTypes.pop(channel["id"])
        return {
            "subbed": subbed,
            "channels": subbedTypes
        }
    
    async def unsubOne(server: dict, serverID: str, channelIDs: list, channelNames: list, subTypes: list, db: mysql.connector.CMySQLConnection):
        """
        Unsubscribe from one or multiple VTuber channels from the Discord channel.
        
        Arguments
        ---
        server: The current channel's subscriptions as a `dict`. (subscription types as keys)
        serverID: The Discord channel's ID.
        channelIDs: The VTuber channel IDs.
        channelNames: The VTuber channel names.
        subTypes: The subscription types to unsubscribe from as a `list`.
        db: A MySQL connection to reduce the amount of unnecessary connections.
        
        Returns
        ---
        A `dict` with:
        - name: The name of the VTuber being unsubscribed from.
        - subTypes: The subscription types given in the respective argument.
        """
        data = {}
        for subType in subTypes:
            data[subType] = await botdb.listConvert(server[subType])
        
        for channelID in channelIDs:
            for subType in data:
                if subType == "twitter":
                    twitter = await botdb.getData(channelID, "id", ("twitter",), "channels", db)
                    if twitter["twitter"] in data[subType]:
                        data[subType].remove(twitter["twitter"])
                        await botdb.addData((serverID, await botdb.listConvert(data[subType])), ("channel", subType), "servers", db)
                elif channelID in data[subType]:
                    data[subType].remove(channelID)
                    await botdb.addData((serverID, await botdb.listConvert(data[subType])), ("channel", subType), "servers", db)
        
        nameText = ""
        if len(channelNames) <= 5:
            for name in channelNames:
                nameText += f"{name}, "
        else:
            nameText = f"{len(channelNames)} channels  "
        return {
            "name": nameText[:-2],
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
