"""
This file is a part of Yagoo Bot <https://yagoo.pleb.moe/>
Copyright (C) 2020-present  ProgrammingPleb

Yagoo Bot is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Yagoo Bot is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Yagoo Bot.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import traceback
import asyncio
import aiohttp
import discord
import logging
from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands, tasks
from yagoo.lib.dataUtils import botdb

async def streamNotify():
    db = await botdb.getDB()
    channels = await botdb.getAllData("scrape", ("id", "name", "image", "streams"), db=db)
    servers = await botdb.getAllData("servers", ("server", "channel", "url", "livestream"), db=db)
    
    async def postMsg(server: dict, channel: dict, video: dict, videoId: str, notified: dict):
        if notified[channel["id"]] != video:
            try:
                async with aiohttp.ClientSession() as session:
                    embed = discord.Embed(title=f'{video["title"]}', url=f'https://youtube.com/watch?v={videoId}')
                    embed.description = f'{video["status"]}'
                    embed.set_image(url=video["thumbnail"])
                    webhook = Webhook.from_url(server["url"], session=session)
                    await webhook.send(f'New livestream from {channel["name"]}!', embed=embed, username=channel["name"], avatar_url=channel["image"])
            except Exception as e:
                if "429 Too Many Requests" in str(e):
                    logging.warning(f"Too many requests for {channel['id']}! Sleeping for 10 seconds.")
                    await asyncio.sleep(10)
                logging.error("Livestreams - An error has occured while publishing a notification!", exc_info=True)
    
    queue = []
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
                                    queue.append(postMsg(server, channel, data[video], video, notified))
                                    await botdb.addData((server["channel"], json.dumps(notified)), ("channel", "notified"), "servers", db=db)
                                except Exception as e:
                                    logging.error("Livestreams - An error has occured while queueing a notification!", exc_info=True)
    
    await asyncio.gather(*queue)

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
            await streamNotify()
        except Exception as e:
            logging.error("Stream - An error has occurred in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.info("Stream checks done.")