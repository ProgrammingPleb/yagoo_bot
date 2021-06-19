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
from ..share.dataUtils import getwebhook

async def premiereCheck():
    with open("data/scrape.json") as f:
        channels = json.load(f)
    channelWrite = False
    
    pInfo = {}
    
    for channel in channels:
        for x in range(3):
            try:
                cInfo = await channelInfo(channel)
                if cInfo["premieres"] != {}:
                    for video in cInfo["premieres"]:
                        vURL = ""
                        if (cInfo["premieres"][video]["time"] - datetime.now().timestamp()) < 60:
                            vURL = await uplThumbnail(channel, video, False)
                        if (cInfo["premieres"][video]["time"] - datetime.now().timestamp()) < 10:
                            pInfo[channel] = {
                                "channel": cInfo["name"],
                                "image": cInfo["image"],
                                "title": cInfo["premieres"][video]["title"],
                                "videoID": video,
                                "thumbnail": vURL
                            }
                            channels[channel]["premieres"].pop(video, "")
                            channelWrite = True
                    break
                else:
                    break
            except Exception as e:
                if x == 2:
                    logging.error(f"Premiere Scrape - Unable to get premieres data for {channel}!", exc_info=True)
    
    if channelWrite:
        with open("data/scrape.json", "w", encoding="utf-8") as f:
            json.dump(channels, f, indent=4)
    
    return pInfo

async def premiereNotify(bot, pData):
    with open("data/servers.json") as f:
        servers = json.load(f)

    for ytch in pData:
        for server in servers:
            for channel in servers[server]:
                if ytch in servers[server][channel]["livestream"]:
                    try:
                        whurl = await getwebhook(bot, servers, server, channel)
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
