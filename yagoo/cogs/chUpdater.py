import logging
import traceback
from discord.ext import commands, tasks
from ..lib.dataUtils import botdb

async def channelUpdate():
    db = await botdb.getDB()
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
        self.chCheck.start()

    def cog_unload(self):
        self.chCheck.cancel()

    @tasks.loop(minutes=30.0)
    async def chCheck(self):
        logging.info("Starting channel update checks.")
        try:
            await channelUpdate()
        except Exception as e:
            logging.error("Channel Update - An error has occurred in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.info("Channel update checks done.")
