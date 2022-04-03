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

import logging
import traceback
import aiomysql
from discord.ext import commands, tasks
from yagoo.lib.dataUtils import botdb

async def channelUpdate(pool: aiomysql.Pool):
    db = await botdb.getDB(pool)
    updates = {}
    scrape = await botdb.getAllData("scrape", ("id", "name", "image"), db=db)
    channels = await botdb.getAllData("channels", ("id", "name", "image"), keyDict="id", db=db)
    
    for channel in scrape:
        if channel["id"] in channels:
            change = False
            temp = {}
            if channel["name"] != channels[channel["id"]]["name"]:
                temp["name"] = channel["name"]
                change = True
            if channel["image"] != channels[channel["id"]]["image"]:
                temp["image"] = channel["image"]
                change = True
            if change:
                updates[channel["id"]] = temp
    
    if len(updates) > 0:
        for channel in updates:
            updateTypes = ["id"]
            updateData = [channel]
            for updateType in updates[channel]:
                updateTypes.append(updateType)
                updateData.append(updates[channel][updateType])
            await botdb.addData(updateData, updateTypes, "channels", db)

class chCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.chCheck.start()

    def cog_unload(self):
        self.chCheck.cancel()

    @tasks.loop(minutes=30.0)
    async def chCheck(self):
        logging.info("Starting channel update checks.")
        try:
            await channelUpdate(self.bot.pool)
        except Exception as e:
            logging.error("Channel Update - An error has occurred in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.info("Channel update checks done.")
