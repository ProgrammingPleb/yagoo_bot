# NOTICE: Marking this as being deprecated
# TODO: Create standalone channel updater

"""import json
import logging
import traceback
from ..infoscraper import channelInfo
from discord.ext import commands, tasks

async def channelCheck():
    with open("data/channels.json") as f:
        channels = json.load(f)
    
    chUpdate = {}

    for channel in channels:
        for x in range(2):
            try:
                ytch = await channelInfo(channel)
                logging.debug(f'Channel Updates - Checking channel: {ytch["name"]}')
                for chUPart in ["name", "image"]:
                    if channels[channel][chUPart] != ytch[chUPart]:
                        chUpdate[channel] = {
                            "name": ytch["name"],
                            "image": ytch["image"],
                            "milestone": channels[channel]["milestone"],
                            "category": channels[channel]["category"]
                        }
                break
            except Exception as e:
                if x == 2:
                    logging.error(f'Channel Updates - Unable to get info for {channel}!')
                    print("An error has occurred.")
                    traceback.print_tb(e)
                    break
                else:
                    logging.warning(f'Channel Updates - Failed to get info for {channel}. Retrying...', exc_info=True)
    
    return chUpdate

async def channelWrite(chUpdate):
    logging.debug(f'Channel Updates Data: {chUpdate}')
    with open("data/channels.json") as f:
        channels = json.load(f)
    
    for channel in chUpdate:
        logging.debug(f"Channel Updates - Updating data for {channel}")
        channels[channel] = chUpdate[channel]
    
    with open("data/channels.json", "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4)

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
            chData = await channelCheck()
            if chData != {}:
                logging.info("Updating channels with new data.")
                await channelWrite(chData)
        except Exception as e:
            logging.error("Channel Update - An error has occurred in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.info("Channel update checks done.")"""
