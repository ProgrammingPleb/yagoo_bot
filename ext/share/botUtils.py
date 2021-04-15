import logging
import discord
import aiohttp
import asyncio
import yaml
import rpyc
from discord.ext import commands
from discord_slash.context import SlashContext
from itertools import islice
from typing import Union
from .prompts import searchConfirm, searchPrompt

def round_down(num, divisor):
    return num - (num%divisor)

def chunks(data, SIZE=10000):
    it = iter(data)
    for i in range(0, len(data), SIZE):
        yield {k:data[k] for k in islice(it, SIZE)}

def creatorCheck(ctx):
    return ctx.author.id == 256009740239241216

def subPerms(ctx):
    userPerms = ctx.channel.permissions_for(ctx.author)
    return userPerms.administrator or userPerms.manage_webhooks or ctx.guild.owner_id == ctx.author.id

async def msgDelete(ctx: Union[commands.Context, SlashContext]):
    if type(ctx) != SlashContext:
        await ctx.message.delete()

class fandomTextParse():
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
                                                                      f"Respond with {partChoice.strip(',')} to look at the section.")

        discordEmbed.set_footer(text="Powered by Fandom", icon_url="https://img.ezz.moe/0407/14-24-14.png")
        return discordEmbed, excessParts

    async def parseData(data):
        dataText = ""

        if type(data) == list:
            for point in data:
                if type(point) == dict:
                    dataText += f'{await fandomTextParse.parseData(point)}'
                else:
                    dataText += f"- {point}\n"
        elif type(data) == dict:
            if "point" in data and "subPoints" in data:
                subPoints = ""
                for subPoint in data["subPoints"]:
                    subPoints += f" • {subPoint}\n"
                dataText += f'- {data["point"]}\n{subPoints.strip()}\n'
            else:
                dataText += f'{await fandomTextParse.parseDict(data)}\n'
        elif type(data) == str:
            dataText += f'{data}\n'
        
        return dataText

    async def parseDict(entry: dict) -> str:
        firstKey = list(entry.keys())[0]
        dictText = f"__{firstKey}__\n"

        for entry in entry[firstKey]:
            dictText += f"{await fandomTextParse.parseData(entry)}"

        return dictText

async def vtuberSearch(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, searchTerm: str, searchMsg):
    from ..infoscraper import FandomScrape, channelInfo
    getChannel = False

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
                        cInfo = await channelInfo(channelID)
                        if not cInfo["success"]:
                            cInfo = await channelInfo(channelID, True)
                        sConfirm = await searchConfirm(ctx, bot, cInfo["name"], searchMsg, f"Subscribe to {cInfo['name']}?", "Subscribe to this channel", "Choose another channel")
                        if sConfirm["success"]:
                            return {
                                "success": True,
                                "channelID": searchTerm,
                                "name": cInfo['name']
                            }
                        elif not sConfirm["success"] and not sConfirm["declined"]:
                            await searchTerm.delete()
                            await msgDelete(ctx)
                            return {
                                "success": False
                            }
    
    if not getChannel:
        fandomSearch = await FandomScrape.searchChannel(searchTerm)

        if fandomSearch["status"] == "Success":
            sConfirm = await searchConfirm(ctx, bot, fandomSearch["name"], searchMsg, f"Subscribe to {fandomSearch['name']}?", "Subscribe to this channel", "Choose another channel")
            if sConfirm["success"]:
                channelID = await FandomScrape.getChannelURL(fandomSearch["name"])
                channelID["name"] = fandomSearch["name"]
                return channelID
            elif not sConfirm["success"] and not sConfirm["declined"]:
                await searchMsg.delete()
                await msgDelete(ctx)
                return {
                    "success": False
                }
        
        if not getChannel or fandomSearch["status"] == "Cannot Match":
            sPick = await searchPrompt(ctx, bot, fandomSearch["results"], searchMsg, "Select a channel to subscribe to:")
            if not sPick["success"]:
                await searchMsg.delete()
                await msgDelete(ctx)
                return {
                    "success": False
                }
            channelID = await FandomScrape.getChannelURL(sPick["name"])
            channelID["name"] = sPick["name"]
            return channelID

async def embedContinue(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, embedMsg: discord.Message, section: str, text: str, name: str):
    textLines = text.split("\n")
    textFormatted = []
    pagePos = 0
    moveChoice = ['h', 'n']
    moveText = ""

    tempText = ""
    for text in textLines:
        if len(f"{tempText}{text}\n") > 950:
            textFormatted.append(tempText)
            tempText = ""
        tempText = f"{tempText}{text}\n"
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
        elif msg.content.lower() == 'n':
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

