import json
import traceback
import aiohttp
import discord
import logging
from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands, tasks
from ..share.dataUtils import botdb

async def streamNotify(bot):
    db = await botdb.getDB()
    channels = await botdb.getAllData("scrape", ("id", "name", "image", "streams"), db=db)
    servers = await botdb.getAllData("servers", ("server", "channel", "url", "livestream"), db=db)
    
    for channel in channels:
        if channel["streams"] != "{}":
            data = json.loads(channel["streams"])
            for server in servers:
                subList = await botdb.listConvert(server["livestream"])
                if subList:
                    for video in data:
                        notifiedData = (await botdb.getData(server["channel"], "channel", ("notified",), "servers", db))["notified"]
                        notified = json.loads(notifiedData)
                        if channel["id"] in subList:
                            if channel["id"] not in notified:
                                notified[channel["id"]] = ""
                            if notified[channel["id"]] != video:
                                notified[channel["id"]] = video
                                try:
                                    async with aiohttp.ClientSession() as session:
                                        embed = discord.Embed(title=f'{data[video]["title"]}', url=f'https://youtube.com/watch?v={video}')
                                        embed.description = f'{data[video]["status"]}'
                                        embed.set_image(url=data[video]["thumbnail"])
                                        webhook = Webhook.from_url(server["url"], adapter=AsyncWebhookAdapter(session))
                                        await webhook.send(f'New livestream from {channel["name"]}!', embed=embed, username=channel["name"], avatar_url=channel["image"])
                                    await botdb.addData((server["channel"], json.dumps(notified)), ("channel", "notified"), "servers", db=db)
                                except Exception as e:
                                    logging.error("Livestreams - An error has occured while publishing a notification!", exc_info=True)

class StreamCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=1.0)
    async def timecheck(self):
        logging.info("Starting stream checks.")
        try:
            await streamNotify(self.bot)
        except Exception as e:
            logging.error("Stream - An error has occurred in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.info("Stream checks done.")