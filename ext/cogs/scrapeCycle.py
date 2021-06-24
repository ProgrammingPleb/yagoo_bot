# NOTE: Marking this as deprecated.
# TODO: Create a standalone channel scraper

"""import logging
import asyncio
import json
import concurrent.futures
import shutil
import os
import traceback
import functools
from discord.ext import commands, tasks
from ..infoscraper import channelInfo

async def channelScrape(debug: bool = False):
    with open("data/channels.json") as f:
        channels = json.load(f)

    async def chScrape(channel, debug):
        for x in range(3):
            try:
                chInfo = await channelInfo(channel, True, debug)
                if not chInfo["success"]:
                    logging.warn(f"Channel Scrape - Retrying to grab channel info for: {channel}")
                else:
                    return chInfo
                await asyncio.sleep(1)
                continue
            except Exception as e:
                if x == 2:
                    logging.error("Channel Scrape - An error has occurred!", exc_info=True)

    chList = []
    for channel in channels:
        chList.append(chScrape(channel, debug))

    chData = await asyncio.gather(*chList)

    for channel in chData:
        try:
            cid = channel["id"]
            channel.pop("id", "id")
            channels[cid] = channel
        except Exception as e:
            logging.error("Channel Scrape - An error has occurred!", exc_info=True)

    with open("data/scrapetemp.json", "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4)
    
    shutil.copyfile("data/scrapetemp.json", "data/scrape.json")
    os.remove("data/scrapetemp.json")

def scrapeWrapper(debug):
    asyncio.run(channelScrape(debug))

class ScrapeCycle(commands.Cog):
    def __init__(self, bot: commands.Bot, debug: bool):
        self.bot = bot
        self.debug = debug
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=3.0)
    async def timecheck(self):
        logging.info("Starting channel scrape.")
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(pool, functools.partial(scrapeWrapper, self.debug))
        except Exception as e:
            logging.error("Channel Scrape - An error has occurred in the cog!")
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.info("Channel scrape done.")

if __name__ == "__main__":
    asyncio.run(channelScrape())"""