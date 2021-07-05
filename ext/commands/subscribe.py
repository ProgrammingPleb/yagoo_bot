import json
import discord
import asyncio
import mysql.connector
from discord.ext import commands
from discord_slash.context import SlashContext
from typing import Union
from ..infoscraper import FandomScrape, channelInfo
from ..share.botUtils import msgDelete, vtuberSearch
from ..share.dataUtils import botdb, dbTools
from ..share.prompts import generalPrompts, subPrompts, subPrompts, subCheck

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
        server = await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), ("subDefault", "livestream", "milestone", "premiere", "twitter"), db)
        subResult = await subUtils.subOne(ctx, bot, searchMsg, server, str(ctx.channel.id), result["channelID"], result["channelName"], db)
        if subResult["status"]:
            await subPrompts.displaySubbed(searchMsg, False, None, subResult["subbed"], result["channelName"])
            return
    await searchMsg.delete()
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
    
    async def channelSearch(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, channel: str = None):
        """
        Searches for a channel with input from the user.
        
        Arguments
        ---
        ctx: Context from the executed command.
        bot: The Discord bot.
        msg: The mesasage that will be used for the prompt.
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

                uConfirm = await subPrompts.vtuberConfirm.prompt(ctx, bot, msg, wikiName["name"])
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
    
    async def subOne(ctx: commands.Context,
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
            if ytChID not in stData:
                stData.append(ytChID)
                await botdb.addData((channelId, await botdb.listConvert(stData)), ("channel", subType), "servers", db)
                subbed.append(subType)
        return {
            "status": True,
            "subbed": subbed
        }
    
    async def subAll(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, server: dict, channelId: str, db: mysql.connector.MySQLConnection, category: str = None):
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
        channel = await botdb.getAllData("channels", ("id", ), category, "category", db=db)
        subDefault = await subUtils.checkDefault(server)
        channels = []
        
        for ch in channel:
            channels.append(ch["id"])
        
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
            newData = list(set(serverType) | set(channels))
            await botdb.addData((channelId, await botdb.listConvert(newData)), ("channel", subType), "servers", db)
        return {
            "status": True,
            "subbed": subDefault
        }
