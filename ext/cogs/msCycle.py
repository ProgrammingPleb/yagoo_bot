import asyncio
import json
import logging
import os
import imgkit
import discord
import traceback
import concurrent.futures
from ..share.dataUtils import botdb
from discord.ext import commands, tasks

async def milestoneCheck():
    db = await botdb.getDB()
    channels = await botdb.getAllData("channels", ("id", "name", "milestone", "image"), db=db)
    scrape = await botdb.getAllData("scrape", ("id", "roundSubs", "mbanner"), keyDict="id", db=db)
    
    async def getSubs(channel: tuple, scrape: dict):
        if channel["milestone"] < scrape["roundSubs"]:
            if scrape["roundSubs"] < 1000000:
                subtext = f'{int(scrape["roundSubs"] / 1000)}K Subscribers'
            else:
                if scrape["roundSubs"] == scrape["roundSubs"] - (scrape["roundSubs"] % 1000000):
                    subtext = f'{int(scrape["roundSubs"] / 1000000)}M Subscribers'
                else:
                    subtext = f'{scrape["roundSubs"] / 1000000}M Subscribers'
            return {
                "id": channel["id"],
                "name": channel["name"],
                "image": channel["image"],
                "banner": scrape["mbanner"],
                "msText": subtext,
                "roundSubs": scrape["roundSubs"]
            }
        return None
    
    queue = []
    for channel in channels:
        if channel["id"] in scrape:
            queue.append(getSubs(channel, scrape[channel["id"]]))
    
    milestone = {}
    dbUpdate = []
    write = False
    results = await asyncio.gather(*queue)
    for result in results:
        if result:
            milestone[result["id"]] = result
            dbUpdate.append((result["id"], result["roundSubs"]))
            write = True
    
    if write:
        await botdb.addMultiData(dbUpdate, ("id", "milestone"), "channels", db)
    
    return milestone

async def milestoneNotify(msDict: dict, bot: commands.Bot):
    db = await botdb.getDB()
    servers = await botdb.getAllData("servers", ("channel", "milestone"), db=db)
    queue = []
    
    async def postMsg(channel: str, server: tuple):
        try:
            await bot.get_channel(int(server["channel"])).send(f'{msDict[channel]["name"]} has reached {msDict[channel]["msText"].replace("Subscribers", "subscribers")}!', file=discord.File(f'milestone/generated/{channel}.png'))
            await bot.get_channel(int(server["channel"])).send("おめでとう！")
        except Exception as e:
            logging.error("Milestone - Failed to post on a server/channel!", exc_info=True)
    
    for channel in msDict:
        if msDict[channel]["banner"] is not None:
            with open("milestone/milestone.html") as f:
                msHTML = f.read()
        else:
            msDict[channel]["banner"] = ""
            with open("milestone/milestone-nobanner.html") as f:
                msHTML = f.read()
        options = {
            "enable-local-file-access": "",
            "encoding": "UTF-8",
            "quiet": ""
        }
        msHTML = msHTML.replace('[msBanner]', msDict[channel]["banner"]).replace('[msImage]', msDict[channel]["image"]).replace('[msName]', msDict[channel]["name"]).replace('[msSubs]', msDict[channel]["msText"])
        with open(f"milestone/{channel}.html", "w", encoding="utf-8") as f:
            f.write(msHTML)
        if not os.path.exists("milestone/generated"):
            os.mkdir("milestone/generated")
        imgkit.from_file(f"milestone/{channel}.html", f'milestone/generated/{channel}.png', options=options)
        os.remove(f"milestone/{channel}.html")
        for server in servers:
            milestone = await botdb.listConvert(server["milestone"])
            if milestone:
                if channel in milestone:
                    queue.append(postMsg(channel, server))
    
    await asyncio.gather(*queue)

def mcWrapper():
    return asyncio.run(milestoneCheck())

class msCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=3.0)
    async def timecheck(self):
        logging.info("Starting milestone checks.")
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                loop = asyncio.get_running_loop()
                msData = await loop.run_in_executor(pool, mcWrapper)
            if msData != {}:
                logging.info("Milestone - Notifying channels.")
                await milestoneNotify(msData, self.bot)
        except Exception as e:
            logging.error("Milestone - An error has occured in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.info("Milestone checks done.")
