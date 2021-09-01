import logging
import discord
import aiohttp
import asyncio
import datetime
import yaml
import rpyc
import tweepy
import mysql.connector
from discord.ext import commands
from discord_slash.context import SlashContext
from itertools import islice
from typing import Union
from yaml.loader import SafeLoader
from .prompts import searchConfirm, searchPrompt
from .dataUtils import botdb

def round_down(num, divisor):
    return num - (num%divisor)

def chunks(data, SIZE=10000):
    it = iter(data)
    for i in range(0, len(data), SIZE):
        yield {k:data[k] for k in islice(it, SIZE)}

def creatorCheck(ctx):
    return ctx.author.id == 256009740239241216

def userWhitelist(ctx):
    with open("data/settings.yaml") as f:
        settings = yaml.load(f, Loader=SafeLoader)
    
    return ctx.author.id in settings["whitelist"]

def subPerms(ctx):
    userPerms = ctx.channel.permissions_for(ctx.author)
    return userPerms.administrator or userPerms.manage_webhooks or ctx.guild.owner_id == ctx.author.id

async def msgDelete(ctx: Union[commands.Context, SlashContext]):
    """
    Removes the message that invoked the command (if any)

    Arguments:
    ---
    `ctx`: A discord.py `commands.Context` or discord-py-slash-commands `SlashContext`
    """
    if type(ctx) != SlashContext:
        await ctx.message.delete()

class fandomTextParse():
    """
    Class that contains functions for Fandom Wiki related actions.
    """
    async def parseToEmbed(name: str, embedData: list):
        embedParts = {}
        excessParts = None
        discordEmbed = discord.Embed(title=name)

        for section in embedData:
            if section["text"] != []:
                embedText = ""
                for entry in section["text"]:
                    embedText += f"{await fandomTextParse.parseData(entry)}"
                embedParts[section["name"]] = embedText
        
        hasLongHT = False
        for section in embedParts:
            longHT = len(embedParts[section]) > 1024
            if not longHT:
                discordEmbed.add_field(name=section, value=embedParts[section].strip(), inline=False)
            else:
                if not hasLongHT:
                    excessParts = {}
                    hasLongHT = True
                excessParts[section] = embedParts[section]
            
        if hasLongHT:
            fieldHeader = ""
            headerCount = 0
            partPhrase = ""
            partChoice = ""
            for part in excessParts:
                fieldHeader += f"{part}/"
                partChoice += f"`{part.lower()}`,"
                headerCount += 1
            if headerCount == 1:
                partPhrase = "this section has"
            elif headerCount > 1:
                partPhrase = "these sections have"
            discordEmbed.add_field(name=fieldHeader.strip("/"), value=f"Due to Discord's limitations, {partPhrase} to be seperated to different embeds.\n"
                                                                      f"Respond with {partChoice.strip(',')} to look at the section.", inline=False)
            discordEmbed.add_field(name="Not the VTuber you're searching for?", value=f"Respond with `search` to choose the correct VTuber.", inline=False)

        discordEmbed.set_footer(text="Powered by Fandom", icon_url="https://img.ezz.moe/0407/14-24-14.png")
        return discordEmbed, excessParts

    async def parseData(data):
        dataText = ""

        if isinstance(data, list):
            for point in data:
                if isinstance(point, dict):
                    dataText += f'{await fandomTextParse.parseData(point)}'
                else:
                    dataText += f"- {point}\n"
        elif isinstance(data, dict):
            if "point" in data and "subPoints" in data:
                subPoints = ""
                for subPoint in data["subPoints"]:
                    subPoints += f" • {subPoint}\n"
                dataText += f'- {data["point"]}\n{subPoints.strip()}\n'
            else:
                dataText += f'{await fandomTextParse.parseDict(data)}\n'
        elif isinstance(data, str):
            dataText += f'{data}\n'
        
        return dataText

    async def parseDict(entries: dict) -> str:
        firstKey = list(entries.keys())[0]
        dictText = f"__{firstKey}__\n"

        for entry in entries[firstKey]:
            dictText += f"{await fandomTextParse.parseData(entry)}"

        return dictText

async def vtuberSearch(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, searchTerm: str, searchMsg, askTerm: str, getOther: bool = False):
    """
    Searches for a VTuber and returns a `dict` with it's relevant data.

    Arguments:
    ---
    `ctx`: A `discord.py` command context or a `discord-py-slash-command` slash context.
    `bot`: A `discord.py` `commands.Bot` object.
    `searchTerm`: The search term that is passed by from the user's input.
    `searchMsg`: A Discord message object that is responsible for the search message.
    `askTerm`: Term used when the search embed says "[askTerm] this channel"
    `getOther`: Whether to have a message confirming the detected VTuber from `searchTerm` or to assume that the first term is correct.
    """
    from ..infoscraper import FandomScrape, channelInfo

    getChannel = False

    if not getOther:
        if "https://www.youtube.com/channel/" in searchTerm:
            for part in searchTerm.split("/"):
                if 23 <= len(part) <= 25:
                    if part[0] == "U":
                        channelID = part
                        getChannel = True
        
        if 23 <= len(searchTerm) <= 25:
            if searchTerm[0] == "U":
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://www.youtube.com/channel/{searchTerm}") as r:
                        if r.status == 200:
                            cInfo = await channelInfo(searchTerm)
                            if not cInfo["success"]:
                                cInfo = await channelInfo(searchTerm, True)
                            sConfirm = await searchConfirm(ctx, bot, cInfo["name"], searchMsg, f"{askTerm} {cInfo['name']}?", f"{askTerm} this channel", "Choose another channel", True)
                            if sConfirm["success"]:
                                return {
                                    "success": True,
                                    "channelID": searchTerm,
                                    "name": cInfo['name']
                                }
                            if not sConfirm["success"] and not sConfirm["declined"]:
                                await searchMsg.delete()
                                await msgDelete(ctx)
                                return {
                                    "success": False
                                }
    
    if not getChannel:
        fandomSearch = await FandomScrape.searchChannel(searchTerm)

        if fandomSearch["status"] == "Success" and not getOther:
            sConfirm = await searchConfirm(ctx, bot, fandomSearch["name"], searchMsg, f"{askTerm} {fandomSearch['name']}?", f"{askTerm} this channel", "Choose another channel")
            if sConfirm["success"]:
                channelID = await FandomScrape.getChannelURL(fandomSearch["name"])
                return {
                    "success": True,
                    "channelID": channelID["channelID"],
                    "name": fandomSearch['name']
                }
            if not sConfirm["success"] and not sConfirm["declined"]:
                await searchMsg.delete()
                await msgDelete(ctx)
                return {
                    "success": False
                }
        
        if not getChannel or fandomSearch["status"] == "Cannot Match":
            sPick = await searchPrompt(ctx, bot, fandomSearch["results"], searchMsg, f"Select a channel to {askTerm.lower()}:")
            if not sPick["success"]:
                await searchMsg.delete()
                await msgDelete(ctx)
                return {
                    "success": False
                }
            channelID = await FandomScrape.getChannelURL(sPick["name"])
            return {
                "success": True,
                "channelID": channelID["channelID"],
                "name": sPick['name']
            }

async def embedContinue(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, embedMsg: discord.Message, section: str, text: str, name: str):
    textLines = text.split("\n")
    textFormatted = []
    pagePos = 0
    moveChoice = ['h', 'n']
    moveText = ""

    tempText = ""
    for textLine in textLines:
        if len(f"{tempText}{textLine}\n") > 950:
            textFormatted.append(tempText)
            tempText = ""
        tempText = f"{tempText}{textLine}\n"
    textFormatted.append(tempText)

    def check(m):
        return m.content.lower() in moveChoice and m.author == ctx.author

    while True:
        if pagePos == 0:
            moveChoice = ['h', 'n']
            moveText = "`h` to go back to the main page, `n` to continue to the next page"
        elif pagePos == len(textFormatted) - 1:
            moveChoice = ['h', 'b']
            moveText = "`h` to go back to the main page, `b` to go back to the previous page"
        else:
            moveChoice = ['h', 'b', 'n']
            moveText = "`h` to go back to the main page, `b` to go back to the previous page, `n` to continue to the next page"

        sectionEmbed = discord.Embed(title=name)
        sectionEmbed.add_field(name=section, value=textFormatted[pagePos], inline=False)
        sectionEmbed.add_field(name="Navigation", value=f"Press {moveText}.", inline=False)
        sectionEmbed.set_footer(text="Powered by Fandom", icon_url="https://img.ezz.moe/0407/14-24-14.png")
        await embedMsg.edit(embed=sectionEmbed)

        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return False

        await msg.delete()
        if msg.content.lower() == 'h':
            return True
        if msg.content.lower() == 'n':
            pagePos += 1
        elif msg.content.lower() == 'p':
            pagePos -= 1

async def formatMilestone(msCount):
    if "M" in msCount:
        cSubsA = int(float(msCount.replace("M subscribers", "")) * 1000000)
        cSubsR = round_down(cSubsA, 500000)
    elif "K" in msCount:
        cSubsA = int(float(msCount.replace("K subscribers", "")) * 1000)
        cSubsR = round_down(cSubsA, 100000)
    else:
        cSubsA = int(float(msCount.replace(" subscribers", "")))
        cSubsR = 0
    
    return cSubsA, cSubsR

async def premiereScrape(ytData):
    pEvents = {}

    try:
        cFirstTab = ytData["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"]

        for oContents in cFirstTab:
            if "shelfRenderer" in oContents["itemSectionRenderer"]["contents"][0]:
                if "horizontalListRenderer" in oContents["itemSectionRenderer"]["contents"][0]["shelfRenderer"]["content"]:
                    for iContents in oContents["itemSectionRenderer"]["contents"][0]["shelfRenderer"]["content"]["horizontalListRenderer"]["items"]:
                        if "gridVideoRenderer" in iContents:
                            if "upcomingEventData" in iContents["gridVideoRenderer"]:
                                for runs in iContents["gridVideoRenderer"]["upcomingEventData"]["upcomingEventText"]["runs"]:
                                    if "Premieres" in runs["text"]:
                                        cPremiereVid = iContents["gridVideoRenderer"]
                                        if cPremiereVid["videoId"] not in pEvents and (int(cPremiereVid["upcomingEventData"]["startTime"]) - datetime.datetime.now().timestamp()) > 10:
                                            pEvents[cPremiereVid["videoId"]] = {
                                                "title": cPremiereVid["title"]["simpleText"],
                                                "time": int(cPremiereVid["upcomingEventData"]["startTime"])
                                            }
    except Exception as e:
        logging.error("Premiere Scrape - An error has occured!", exc_info=True)

    return pEvents

async def uplThumbnail(channelID, videoID, live=True):
    with open("data/settings.yaml") as f:
        settings = yaml.load(f, Loader=yaml.SafeLoader)
    extServer = rpyc.connect(settings["thumbnailIP"], int(settings["thumbnailPort"]))
    asyncUpl = rpyc.async_(extServer.root.thumbGrab)
    uplSuccess = False

    for x in range(3):
        if live:
            upload = asyncUpl(channelID, f'https://img.youtube.com/vi/{videoID}/maxresdefault_live.jpg')
        else:
            upload = asyncUpl(channelID, f'https://img.youtube.com/vi/{videoID}/maxresdefault.jpg')
        uplSuccess = False

        while True:
            if upload.ready and not upload.error:
                logging.debug("Stream - Uploaded thumbnail!")
                uplSuccess = True
                break
            elif upload.error:
                break

            await asyncio.sleep(0.5)

        if not uplSuccess or "yagoo.ezz.moe" not in upload.value:
            logging.error("Stream - Couldn't upload thumbnail!")
            logging.error(upload.value)
        else:
            return upload.value

async def serverSubTypes(msg: discord.Message, subDNum: list, subOptions: list) -> dict:
    """
    Gives subscription types from the input message.

    Arguments
    ---
    `msg`: A Discord message object containing the user's input.
    `subDNum`: List containing subscription type number (and letter) assignments.
    `subOptions`: List containing all available subscription types.

    Returns a `dict` object containing:
    `success`: Boolean that returns `True` if the message is valid.
    `subType`: List that has all subscription types.
    """
    valid = True
    subUChoice = []

    try:
        if "," in msg.content:
            for choice in msg.content.split(","):
                if choice != '':
                    subUChoice.append(int(choice))
        else:
            subUChoice.append(int(msg.content))
    except ValueError:
            valid = False

    if valid:
        subType = []
        try:
            if int(subDNum[-2]) not in subUChoice:
                for subUType in subUChoice:
                    subType.append(subOptions[subUType - 1].lower())
            else:
                for subUType in subOptions:
                    subType.append(subUType.lower())
        except Exception as e:
            return {
                "success": False,
                "subType": None
            }
        return {
            "success": True,
            "subType": subType
        }
    return {
        "success": False,
        "subType": None
    }

class TwitterUtils:
    """
    Twitter-related utilities to be used by the bot's functions.
    """

    async def dbExists(twtID: str, db: mysql.connector.CMySQLConnection = None):
        """
        Checks if the supplied Twitter user ID exists in the bot's Twitter database.
        
        Arguments
        ---
        twtID: A Twitter user's ID in string format.
        db: An existing MySQL connection to avoid making a new uncesssary connection.

        Returns
        ---
        A `dict` containing:
        - status: `True` if the user exists in the database, `False` if otherwise.
        - user: User's account data if `status` is `True`, `None` if otherwise.
        """
        if not db:
            db = await botdb.getDB()
        
        result = await botdb.getData(twtID, "twtID", ("twtID", ), "twitter", db)
        
        if result:
            return {
                "status": True,
                "user": result["twtID"]
            }
        return {
            "status": False,
            "user": None
        }

    async def newAccount(userData: tweepy.User, db: mysql.connector.CMySQLConnection = None):
        """
        Adds a new Twitter account to the bot's database.

        Arguments
        ---
        userData: The account's data (from `tweepy.User`)
        db: An existing MySQL connection to avoid making a new uncesssary connection.
        """
        if not db:
            db = await botdb.getDB()
        
        await botdb.addData((userData.id_str, 1, userData.name, userData.screen_name),
                            ("twtID", "custom", "name", "screenName"), "twitter", db)
    
    async def followActions(action: str, channel: str, userID: str = None, allAccounts: bool = False, db: mysql.connector.CMySQLConnection = None):
        """
        Follow or unfollow a user based on the action argument given. Saves it inside the bot's database.

        Arguments
        ---
        action: Can be either `add` to follow or `remove` to unfollow.
        channel: The channel's ID in `str` type.
        userID: The user's Twitter ID. Optional if `all` is set to `True`.
        all: Selects all currently followed users of the channel. Can be used only if `action` is `remove`.
        db: An existing MySQL connection to avoid making a new uncesssary connection.

        Returns
        ---
        `True` if the action was successful, `False` if otherwise.
        """
        if not db:
            db = await botdb.getDB()
        
        server = await botdb.getData(channel, "channel", ("custom", ), "servers", db)
        custom = await botdb.listConvert(server["custom"])
        if not custom:
            custom = []
        
        if action == "add":
            if userID not in custom:
                custom.append(userID)
            else:
                return False
        elif action == "remove":
            if allAccounts:
                custom = []
            elif userID != []:
                for x in userID:
                    custom.remove(x)
            else:
                return False
        
        await botdb.addData((channel, await botdb.listConvert(custom)), ("channel", "custom"), "servers", db)
        return True
    
    async def getScreenName(accLink: str):
        """
        Get the screen name from a Twitter account/tweet link.\n
        Can also be grabbed from just the Twitter screen name with or without the `@`.

        Arguments
        ---
        accLink: The string containing one of either situations above.

        Returns
        ---
        The screen name obtained from `accLink`.
        """
        if "twitter.com" in accLink:
            nextSection = False
            for section in accLink.split("/"):
                if nextSection:
                    twtHandle = section
                    break
                if section == "twitter.com":
                    nextSection = True
        elif "@" in accLink:
            twtHandle = accLink.split("@")[-1]
        else:
            twtHandle = accLink
        
        return twtHandle
