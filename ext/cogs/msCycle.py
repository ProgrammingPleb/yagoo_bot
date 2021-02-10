import json
import logging
import os
import imgkit
import discord
import traceback
from ..infoscraper import channelInfo
from discord.ext import commands, tasks

async def milestoneCheck():
    with open("data/channels.json") as f:
        channels = json.load(f)
    
    milestone = {}
    noWrite = True

    for channel in channels:
        for x in range(2):
            try:
                ytch = await channelInfo(channel)
                logging.debug(f'Milestone - Checking channel: {ytch["name"]}')
                if ytch["roundSubs"] > channels[channel]["milestone"]:
                    noWrite = False
                    if ytch["roundSubs"] < 1000000:
                        subtext = f'{int(ytch["roundSubs"] / 1000)}K Subscribers'
                    else:
                        if ytch["roundSubs"] == ytch["roundSubs"] - (ytch["roundSubs"] % 1000000):
                            subtext = f'{int(ytch["roundSubs"] / 1000000)}M Subscribers'
                        else:
                            subtext = f'{ytch["roundSubs"] / 1000000}M Subscribers'
                    milestone[channel] = {
                        "name": ytch["name"],
                        "image": ytch["image"],
                        "banner": ytch["mbanner"],
                        "msText": subtext
                    }
                    channels[channel]["milestone"] = ytch["roundSubs"]
                    break
            except Exception as e:
                if x == 2:
                    logging.error(f'Milestone - Unable to get info for {channel}!')
                    print("An error has occurred.")
                    traceback.print_tb(e)
                    break
                else:
                    logging.warning(f'Milestone - Failed to get info for {channel}. Retrying...')
    
    if not noWrite:
        with open("data/channels.json", "w") as f:
            json.dump(channels, f, indent=4)
    
    return milestone

async def milestoneNotify(msDict, bot):
    logging.debug(f'Milestone Data: {msDict}')
    with open("data/servers.json") as f:
        servers = json.load(f)
    for channel in msDict:
        logging.debug(f'Generating milestone image for id {channel}')
        if msDict[channel]["banner"] is not None:
            with open("milestone/milestone.html") as f:
                msHTML = f.read()
        else:
            with open("milestone/milestone-nobanner.html") as f:
                msHTML = f.read()
        options = {
            "enable-local-file-access": "",
            "encoding": "UTF-8",
            "quiet": ""
        }
        msHTML = msHTML.replace('[msBanner]', msDict[channel]["banner"]).replace('[msImage]', msDict[channel]["image"]).replace('[msName]', msDict[channel]["name"]).replace('[msSubs]', msDict[channel]["msText"])
        logging.debug(f'Replaced HTML code')
        with open("milestone/msTemp.html", "w", encoding="utf-8") as f:
            f.write(msHTML)
        logging.debug(f'Generating image for milestone')
        if not os.path.exists("milestone/generated"):
            os.mkdir("milestone/generated")
        imgkit.from_file("milestone/msTemp.html", f'milestone/generated/{channel}.png', options=options)
        logging.debug(f'Removed temporary HTML file')
        os.remove("milestone/msTemp.html")
        for server in servers:
            logging.debug(f'Accessing server id {server}')
            for dch in servers[server]:
                logging.debug(f'Milestone - Channel Data: {servers[server][dch]["milestone"]}')
                logging.debug(f'Milestone - Channel Check Pass: {channel in servers[server][dch]["milestone"]}')
                if channel in servers[server][dch]["milestone"]:
                    logging.debug(f'Posting to {dch}...')
                    await bot.get_channel(int(dch)).send(f'{msDict[channel]["name"]} has reached {msDict[channel]["msText"].replace("Subscribers", "subscribers")}!', file=discord.File(f'milestone/generated/{channel}.png'))
                    await bot.get_channel(int(dch)).send("おめでとう！")

class msCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=3.0)
    async def timecheck(self):
        logging.info("Starting milestone checks.")
        msData = await milestoneCheck()
        if msData != {}:
            logging.info("Notifying channels (Milestone).")
            await milestoneNotify(msData, self.bot)
        logging.info("Milestone checks done.")