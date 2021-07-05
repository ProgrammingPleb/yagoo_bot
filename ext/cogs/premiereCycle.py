from datetime import datetime
from ext.share.botUtils import uplThumbnail
import logging
import aiohttp
import discord
import traceback
import json
from discord.ext import commands, tasks
from discord import Webhook, AsyncWebhookAdapter
from ..infoscraper import channelInfo
from ..share.dataUtils import getWebhook, botdb

async def premiereCheck():
    channels = await botdb.getAllData("scrape", ("id", "name", "image", "premieres"))
    pInfo = {}
    
    for channel in channels:
        premieres = json.loads(channel["premieres"])
        if premieres != {}:
            for video in premieres:
                vURL = ""
                if (premieres[video]["time"] - datetime.now().timestamp()) < 60:
                    vURL = await uplThumbnail(channel, video, False)
                if (premieres[video]["time"] - datetime.now().timestamp()) < 10:
                    pInfo[channel] = {
                        "channel": channel["name"],
                        "image": channel["image"],
                        "title": premieres[video]["title"],
                        "videoID": video,
                        "thumbnail": vURL
                    }
    
    return pInfo

# TODO: Use getWebhook for use with SQL
async def premiereNotify(bot, pData):
    servers = await botdb.getAllData("servers", ("server", "channel", "premiere"))

    for ytch in pData:
        for row in servers:
            if ytch in row["premiere"].split("|yb|"):
                try:
                    whurl = await getwebhook(bot, servers, row["server"], row["channel"])
                    async with aiohttp.ClientSession() as session:
                        embed = discord.Embed(title=f'{pData[ytch]["title"]}', url=f'https://youtube.com/watch?v={pData[ytch]["videoID"]}')
                        embed.description = f'Premiering Now'
                        embed.set_image(url=pData[ytch]["thumbnail"])
                        webhook = Webhook.from_url(whurl, adapter=AsyncWebhookAdapter(session))
                        await webhook.send(f'New premiere from {pData[ytch]["channel"]}!', embed=embed, username=pData[ytch]["channel"], avatar_url=pData[ytch]["image"])
                except Exception as e:
                    logging.error(f"Stream - An error has occurred while publishing premiere notification to {channel}!", exc_info=True)
                    break

class PremiereCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(seconds=5.0)
    async def timecheck(self):
        logging.debug("Starting premiere checks.")
        try:
            pData = await premiereCheck()
            if pData != {}:
                logging.info("Premieres - Notifying channels.")
                await premiereNotify(self.bot, pData)
        except Exception as e:
            logging.error("Premieres - An error has occurred in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.debug("Premiere checks done.")
