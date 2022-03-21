import discord
import mysql.connector
from discord.ext import commands
from typing import Union, List
from yagoo.types.data import ChannelSubscriptionData, FandomChannel, SubscriptionData, SubscriptionResponse, UnsubscriptionResponse, YouTubeChannel
from yagoo.types.error import NoSubscriptions
from yagoo.types.message import YagooMessage
from yagoo.scrapers.infoscraper import FandomScrape, channelInfo
from yagoo.lib.botUtils import msgDelete
from yagoo.lib.botVars import allSubTypes
from yagoo.lib.dataUtils import botdb, dbTools
from yagoo.lib.prompts import checkCancel, removeMessage, subPrompts, unsubPrompts
from yagoo.types.views import YagooSelectOption, YagooViewResponse

async def subCategory(cmd: Union[commands.Context, discord.Interaction], bot: commands.Bot):
    """
    Subscription prompt that uses a category and channel based selection.
    
    Arguments
    ---
    cmd: Context or interaction from the executed command.
    bot: The Discord bot.
    """
    db = await botdb.getDB()
    if isinstance(cmd, commands.Context):
        message = YagooMessage(bot, cmd.author)
        message.msg = await cmd.send("Loading channels list...")
    else:
        message = YagooMessage(bot, cmd.user)
    
    channels = await botdb.getAllData("channels", ("id", "category"), keyDict="id", db=db)
    ctgPick = await subPrompts.ctgPicker(cmd, channels, message)
    
    if checkCancel(ctgPick):
        await removeMessage(message, cmd)
        return
    
    server = await dbTools.serverGrab(bot, str(cmd.guild.id), str(cmd.channel.id), ("subDefault", "livestream", "milestone", "premiere", "twitter"), db)
    if ctgPick.buttonID == "all":
        subResult = await subUtils.subAll(cmd, message, server, str(cmd.channel.id), db)
        subResult.channelNames = ["all VTubers"]
        else:
        channels = await botdb.getAllData("channels", ("id", "name"), ctgPick.selectValues[0], "category", keyDict="id", db=db)
        result = await subPrompts.channelPick.prompt(cmd, message, channels, ctgPick.selectValues[0])
        if result.status:
            if result.allInCategory:
                subResult = await subUtils.subAll(cmd, message, server, str(cmd.channel.id), db, ctgPick.selectValues[0])
                subResult.channelNames = [f"all {ctgPick.selectValues[0]} VTubers"]
    else:
                subResult = await subUtils.subOne(cmd, message, server, str(cmd.channel.id), result.channels, db)
                else:
            subResult = SubscriptionResponse(False)
    if subResult.status:
        await subPrompts.displaySubbed(message, subResult)
        await removeMessage(cmd=cmd)
        return
    await removeMessage(message, cmd)

async def subCustom(cmd: Union[commands.Context, discord.Interaction], bot: commands.Bot, search: str):
    """
    Subscribes to a VTuber with the channel name provided to the user.
    
    Arguments
    ---
    ctx: Context from the executed command.
    bot: The Discord bot.
    search: The name of the channel to search for.
    """
    db = await botdb.getDB()
    if isinstance(cmd, commands.Context):
        message = YagooMessage(bot, cmd.author)
        message.msg = await cmd.send("Loading channels list...")
    else:
        message = YagooMessage(bot, cmd.user)
    
    result = await subUtils.channelSearch(cmd, message, search)
    if result.success:
        server = await dbTools.serverGrab(bot, str(cmd.guild.id), str(cmd.channel.id), tuple(["subDefault"] +  allSubTypes(False)), db)
        subResult = await subUtils.subOne(cmd, message, server, str(cmd.channel.id), [YouTubeChannel(result.channelID, result.channelName)], db)
        if subResult.status:
            await subPrompts.displaySubbed(message, subResult)
            await removeMessage(cmd=cmd)
            return
    await removeMessage(message, cmd)

async def unsubChannel(cmd: Union[commands.Context, discord.Interaction], bot: commands.Bot, channel: str = None):
    """
    Unsubscribes from a VTuber. (bypasses a prompt if a channel is given)
    
    Arguments
    ---
    ctx: Context or interaction from the invoked command.
    bot: The Discord bot.
    channel: The search term for the VTuber.
    """
    db = await botdb.getDB()
    if isinstance(cmd, commands.Context):
        message = YagooMessage(bot, cmd.author)
        message.msg = await cmd.send("Loading channel subscriptions...")
    else:
        message = YagooMessage(bot, cmd.user)
    server = await dbTools.serverGrab(bot, str(cmd.guild.id), str(cmd.channel.id), tuple(allSubTypes(False)), db)
    
    subData = await unsubUtils.parseToSubTypes(server, db)
    if not subData.exists:
        raise NoSubscriptions(cmd.channel.id)
    if not channel:
        message.resetMessage()
        message.embed.title = "Unsubscribing from VTuber Channels"
        message.embed.description = "Choose the VTuber(s) to be unsubscribed from."
        message.embed.add_field(name="Searching for a VTuber?", value="Enter the VTuber's name after the `unsubscribe` command.")
        message.addSelect(await unsubUtils.parseToPages(subData), "Choose the VTuber(s) here", max_values=25)
        message.addButton(2, "search", label="Search for a VTuber", disabled=True)
        message.addButton(2, "all", "Unsubscribe from all VTubers")
        message.addButton(3, "cancel", "Cancel", style=discord.ButtonStyle.red)
        
        if isinstance(cmd, commands.Context):
            result = await message.legacyPost(cmd)
    else:
            result = await message.post(cmd, True, True)
        else:
        wikiName = await subUtils.channelSearch(cmd, message, channel, "unsubscribe")
        if wikiName.success:
            result = YagooViewResponse()
            result.responseType = "select"
            result.selectValues = [wikiName.channelID]
        else:
            result = YagooViewResponse()
    
    if result.responseType:
        if result.buttonID == "all":
            unsubResult = await unsubPrompts.removePrompt.prompt(cmd, message, None, subData, True)
            if not unsubResult.status:
                return await removeMessage(message, cmd)
            await unsubUtils.unsubAll(str(cmd.channel.id), unsubResult, db)
        elif result.buttonID == "cancel":
            return await removeMessage(message, cmd)
        else:
            unsubResult = await unsubPrompts.removePrompt.prompt(cmd, message, result.selectValues, subData)
            if not unsubResult.status:
                return await removeMessage(message, cmd)
            await unsubUtils.unsubOne(server, str(cmd.channel.id), unsubResult, db)
        await unsubPrompts.displayResult(message, unsubResult)
        return await removeMessage(cmd=cmd)
    await removeMessage(message, cmd)

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
    
    async def channelSearch(cmd: Union[commands.Context, discord.Interaction], message: YagooMessage, channel: str, action: str = "subscribe"):
        """
        Searches for a channel with input from the user.
        
        Arguments
        ---
        ctx: Context or interaction from the invoked command.
        message: The message that will be used for the prompt.
        channel: The name of the channel if already provided by the user.
        action: The action that is currently is being done with this search.
        
        Result
        ---
        A `dict` with:
        - status: `True` if the user successfully searches for a VTuber.
        - channelID: The channel ID of the VTuber channel.
        - channelName: The name of the channel.
        """
        wikiName = await FandomScrape.searchChannel(channel)
            
            while True:
            if wikiName.status.cannotMatch:
                wikiName = await subPrompts.searchPick(cmd, message, channel, wikiName)

                if not wikiName.status.matched:
                    return FandomChannel()

            uConfirm = await subPrompts.vtuberConfirm.prompt(cmd, message, wikiName.channelName, action)
            if uConfirm.responseType:
                if uConfirm.buttonID == "confirm":
                        break
                elif uConfirm.buttonID == "results":
                    wikiName.cannotMatch()
                    else:
                    return FandomChannel()
                else:
                return FandomChannel()
            
        channelData = await FandomScrape.getChannelURL(wikiName.channelName)
        if channelData.success:
                db = await botdb.getDB()
            if not await botdb.checkIfExists(channelData.channelID, "id", "channels", db):
                message.resetEmbed()
                message.embed.title = "Getting Channel Data..."
                message.embed.description = "This channel is new in the database.\nPlease wait while we're getting the channel's info."
                message.embed.color = discord.Color.from_rgb(0, 0, 0)
                message.msg = await message.msg.edit(content=None, embed=message.embed, view=None)
                chData = await subUtils.addChannel(channelData.channelID, channelData.channelName, ("id", "name"), db)
                else:
                chData = await botdb.getData(channelData.channelID, "id", ("id", "name"), "channels", db)
            return FandomChannel(True, chData["id"], chData["name"])
        return FandomChannel()
    
    async def subOne(cmd: commands.Context,
                     message: YagooMessage,
                     server: dict,
                     channelId: str,
                     channels: List[YouTubeChannel],
                     db: mysql.connector.MySQLConnection):
        """
        Subscribes to one/multiple channel(s) with the specified channel ID(s).
        
        Arguments
        ---
        cmd: Context or interaction from the executed command.
        msg: The message that will be used as a prompt.
        server: The server as a `dict` containing `subDefault` and other subscription types.
        channelId: The channel ID of the current Discord channel.
        channels: A `list` of `YouTubeChannel` of the currently being subscribed channels.
        db: An existing MySQL connection to reduce unnecessary connections.
        
        Returns
        ---
        An instance of `SubscriptionResponse`
        """
        subDefault = await subUtils.checkDefault(server)
        subbed = []
        
        if len(channels) > 1:
            ytChName = "Multiple Channels"
        else:
            ytChName = channels[0].channelName
        if subDefault == [''] or subDefault is None:
            message.resetEmbed()
            message.embed.title = f"Subscribing to {ytChName}"
            message.embed.description = "Pick the notifications to be posted to this channel.\n" \
                                        "(This prompt can be bypassed by setting a default subscription type " \
                                        "using the `subDefault` command)"
            result = await subPrompts.subTypes.prompt(cmd, message)
            if isinstance(result, YagooViewResponse):
                if not result.responseType:
                    return SubscriptionResponse(False)
            subDefault = []
            for subType in result.subList:
                if result.subList[subType]:
                    subDefault.append(subType)
        for channel in channels:
            for subType in subDefault:
                stData = await botdb.listConvert(server[subType])
                if not stData:
                    stData = []
                if subType == "twitter":
                    twitter = (await botdb.getData(channel.channelID, "id", ("twitter", ), "channels", db))["twitter"]
                    if twitter is not None:
                        if twitter not in stData:
                            stData.append(twitter)
                            server[subType] = await botdb.listConvert(stData)
                            await botdb.addData((channelId, await botdb.listConvert(stData)), ("channel", subType), "servers", db)
                            if subType not in subbed:
                                subbed.append(subType)
                else:
                    if channel.channelID not in stData:
                        stData.append(channel.channelID)
                        server[subType] = await botdb.listConvert(stData)
                        await botdb.addData((channelId, await botdb.listConvert(stData)), ("channel", subType), "servers", db)
                        if subType not in subbed:
                            subbed.append(subType)
        if len(channels) <= 5:
            channelNames = []
            for channel in channels:
                channelNames.append(channel.channelName)
        else:
            channelNames = [f"{len(channels)} channels"]
        return SubscriptionResponse(True, subbed, channelNames=channelNames)
    
    async def subAll(cmd: Union[commands.Context, discord.Interaction],
                     message: YagooMessage,
                     server: dict,
                     channelId: str,
                     db: mysql.connector.MySQLConnection,
                     category: str = None):
        """
        Subscribes to all channels (in a category if specified, every channel if otherwise).
        
        Arguments
        ---
        cmd: Context or interaction from the invoked command.
        bot: The Discord bot.
        message: The message that will be used for prompts.
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
            message.resetEmbed()
            message.embed.title = f"Subscribing to all {category}VTubers"
            message.embed.description = "Pick the notifications to be posted to this channel.\n" \
                                        "(This prompt can be bypassed by setting a default subscription type " \
                                        "using the `subDefault` command)"
            result = await subPrompts.subTypes.prompt(cmd, message)
            if isinstance(result, SubscriptionData):
                for subType in result.subList:
                    if result.subList[subType]:
                        subDefault.append(subType)
            else:
                return SubscriptionResponse(False)
        for subType in subDefault:
            serverType = await botdb.listConvert(server[subType])
            if serverType is None:
                serverType = []
            if subType != "twitter":
                newData = list(set(serverType) | set(channels))
            else:
                newData = list(set(serverType) | set(twitter))
            await botdb.addData((channelId, await botdb.listConvert(newData)), ("channel", subType), "servers", db)
        return SubscriptionResponse(True, subDefault)

class unsubUtils:
    async def parseToPages(subData: ChannelSubscriptionData):
        """
        Parses the current channel's subscriptions into a page format to be used in `pageNav.message()`.
        
        Arguments
        ---
        subData: The channel's subscription data.
        
        Returns
        ---
        A `list` containing `YagooSelectOption`.
        """
        result = []
        
        for channel in subData.allChannels:
            result.append(YagooSelectOption(channel.channelName, channel.channelID))
        
        return result
    
    async def parseToSubTypes(server: dict, db: mysql.connector.MySQLConnection):
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
        channelSubbed = {}
        channelSubs = ChannelSubscriptionData()
        for subType in subTypes:
            temp = await botdb.listConvert(server[subType])
            if temp is None:
                temp = []
            if temp != [] and not channelSubs.exists:
                channelSubs.exists = True
            channelSubbed[subType] = temp
        
        if channelSubs.exists:
        for channel in channels:
            if channel["id"] not in subbed:
                for subType in subTypes:
                        if channel["id"] in channelSubbed[subType] or channel["twitter"] in channelSubbed[subType]:
                        if subType != "twitter":
                                channelSubs.addChannel(subType, channel["id"], channel["name"])
                        else:
                                channelSubs.addChannel(subType, channel["id"], channel["name"], channel["twitter"])
        return channelSubs
    
    async def unsubOne(server: dict, serverID: str, unsubData: UnsubscriptionResponse, db: mysql.connector.MySQLConnection):
        """
        Unsubscribe from one or multiple VTuber channels from the Discord channel.
        
        Arguments
        ---
        server: The current channel's subscriptions as a `dict`. (subscription types as keys)
        serverID: The Discord channel's ID.
        unsubData: The unsubscription data.
        db: A MySQL connection to reduce the amount of unnecessary connections.
        
        Returns
        ---
        A `dict` with:
        - name: The name of the VTuber being unsubscribed from.
        - subTypes: The subscription types given in the respective argument.
        """
        data = {}
        for subType in unsubData.subTypes:
            data[subType] = await botdb.listConvert(server[subType])
        
        for channel in unsubData.channels:
            for subType in data:
                if subType == "twitter" and channel.twitter:
                    if channel.twitter in data[subType]:
                        data[subType].remove(channel.twitter)
                        await botdb.addData((serverID, await botdb.listConvert(data[subType])), ("channel", subType), "servers", db)
                elif channel.channelID in data[subType]:
                    data[subType].remove(channel.channelID)
                    await botdb.addData((serverID, await botdb.listConvert(data[subType])), ("channel", subType), "servers", db)
    
    async def unsubAll(serverID: str, unsubData: UnsubscriptionResponse, db: mysql.connector.MySQLConnection):
        """
        Unsubscribe from every VTuber channel from the Discord channel.
        
        Arguments
        ---
        serverID: The Discord channel's ID.
        unsubData: The unsubscription data.
        db: A MySQL connection to reduce the amount of unnecessary connections.
        
        Returns
        ---
        A `dict` with:
        - name: The name of the VTuber being unsubscribed from. (`all Vtubers`)
        - subTypes: The subscription types given in the respective argument.
        """
        for subType in unsubData.subTypes:
            await botdb.deleteCell(subType, serverID, "channel", "servers", db)
