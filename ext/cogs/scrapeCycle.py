import logging
import asyncio
import json
import concurrent.futures
from discord.ext import commands, tasks
from ..infoscraper import channelInfo

async def channelScrape():
    with open("data/channels.json") as f:
        channels = json.load(f)

    async def chRetry(channel):
        for x in range(3):
            try:
                chInfo = await channelInfo(channel, True)
                if not chInfo["success"]:
                    continue
                else:
                    return chInfo
            except Exception as e:
                if x == 2:
                    logging.error("Channel Scrape - An error has occurred!", exc_info=True)

    chList = []
    for channel in channels:
        chList.append(chRetry(channel))

    chData = await asyncio.gather(*chList)

    for channel in chData:
        try:
            cid = channel["id"]
            channel.pop("id", "id")
            channels[cid] = channel
        except Exception as e:
            logging.error("Channel Scrape - An error has occurred!", exc_info=True)

    with open("data/scrape.json", "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4)

def scrapeWrapper():
    asyncio.run(channelScrape())

class ScrapeCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=3.0)
    async def timecheck(self):
        logging.info("Starting channel scrape.")
        with concurrent.futures.ThreadPoolExecutor() as pool:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(pool, scrapeWrapper)
        logging.info("Channel scrape done.")

if __name__ == "__main__":
    asyncio.run(channelScrape())