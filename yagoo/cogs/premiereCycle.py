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

import asyncio
import logging
import aiohttp
import discord
import traceback
import json
from discord.ext import commands, tasks
from discord import Webhook, AsyncWebhookAdapter
from datetime import datetime
from yagoo.lib.dataUtils import botdb

async def premiereNotify():
    db = await botdb.getDB()
    servers = await botdb.getAllData("servers", ("server", "channel", "url", "premiere"), db=db)
    channels = await botdb.getAllData("scrape", ("id", "name", "image", "premieres"), db=db)

    async def postMsg(server: dict, channel: dict, video: dict, videoId: str, notified: dict):
        if notified[channel["id"]] != video:
            try:
                async with aiohttp.ClientSession() as session:
                    embed = discord.Embed(title=f'{video["title"]}', url=f'https://youtube.com/watch?v={videoId}')
                    embed.description = f'Premiering Now'
                    embed.set_image(url=video["thumbnail"])
                    webhook = Webhook.from_url(server["url"], session=session)
                    await webhook.send(f'New premiere from {channel["name"]}!', embed=embed, username=channel["name"], avatar_url=channel["image"])
            except Exception as e:
                if "429 Too Many Requests" in str(e):
                    logging.warning(f"Too many requests for {channel['id']}! Sleeping for 10 seconds.")
                    await asyncio.sleep(10)
                logging.error("Premieres - An error has occured while publishing a notification!", exc_info=True)

    queue = []
    for channel in channels:
        if channel["premieres"] != "{}":
            premieres = json.loads(channel["premieres"])
            for server in servers:
                subList = await botdb.listConvert(server["premiere"])
                if subList:
                    if channel["id"] in subList:
                        notifiedData = (await botdb.getData(server["channel"], "channel", ("notified",), "servers", db))["notified"]
                        notified = json.loads(notifiedData)
                        
                        for video in premieres:
                            if int(premieres[video]["upcoming"]) < datetime.now().timestamp():
                                if channel["id"] not in notified:
                                    notified[channel["id"]] = ""
                                if notified[channel["id"]] != video:
                                    queue.append(postMsg(server, channel, premieres[video], video, notified))
                                    notified[channel["id"]] = video
                                    await botdb.addData((server["channel"], json.dumps(notified)), ("channel", "notified"), "servers", db)
    
    await asyncio.gather(*queue)

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
            await premiereNotify()
        except Exception as e:
            logging.error("Premieres - An error has occurred in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.debug("Premiere checks done.")
