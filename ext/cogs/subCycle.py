import json
import traceback
import aiohttp
import discord
import logging
import rpyc
import yaml
import asyncio
import concurrent.futures
from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands, tasks
from ..infoscraper import streamInfo, channelInfo
from ..share.dataGrab import getwebhook
from ..share.prompts import botError

async def streamcheck(ctx = None, test: bool = False, loop: bool = False):
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    with open("data/settings.yaml") as f:
        settings = yaml.load(f, Loader=yaml.SafeLoader)
    extServer = rpyc.connect(settings["thumbnailIP"], int(settings["thumbnailPort"]))
    asyncUpl = rpyc.async_(extServer.root.thumbGrab)

    async def channelCheck(channel):
        for x in range(2):
            try:
                status = await streamInfo(channel)
                ytchannel = await channelInfo(channel)
                logging.debug(status)
                if status["isLive"]:
                    logging.debug(f'Stream - {ytchannel["name"]} is live!')
                    logging.debug("Stream - Sending upload command to thumbnail server...")

                    upload = asyncUpl(channel, f'https://img.youtube.com/vi/{status["videoId"]}/maxresdefault_live.jpg')
                    uplSuccess = False

                    for x in range(3):
                        upload = asyncUpl(channel, f'https://img.youtube.com/vi/{status["videoId"]}/maxresdefault_live.jpg')
                        uplSuccess = False

                        while True:
                            if upload.ready and not upload.error:
                                logging.debug("Stream - Uploaded thumbnail!")
                                uplSuccess = True
                                break
                            elif upload.error:
                                break

                            await asyncio.sleep(0.5)

                        if not uplSuccess or "yagoo.ezz.moe" not in upload.value:
                            logging.error("Stream - Couldn't upload thumbnail!")
                            logging.error(upload.value)
                        else:
                            break
                    
                    return {
                        "id": channel,
                        "name": ytchannel["name"],
                        "image": ytchannel["image"],
                        "videoId": status["videoId"],
                        "videoTitle": status["videoTitle"],
                        "timeText": status["timeText"],
                        "thumbURL": upload.value
                    }
            except Exception as e:
                if x == 1:
                    logging.error(f"Stream - An error has occured! (Channel ID: {channel})", exc_info=True)

    if not test:
        try:
            chList = []
            chNotify = {}
            for channel in channels:
                chList.append(channelCheck(channel))
            liveCh = await asyncio.gather(*chList)
            logging.debug(f'Stream - Current livestream data:\n{liveCh}')
            for channel in liveCh:
                if channel is not None:
                    cid = channel["id"]
                    channel.pop("id")
                    chNotify[cid] = channel
            return chNotify
        except Exception as e:
            logging.error(f"Stream - An error has occured! (Channel ID: {channel})", exc_info=True)

    """stext = ""
    stext2 = ""
    for channel in channels:
        for x in range(2):
            try:
                # print(f'Checking {cshrt["name"]}...')
                if channel != "":
                    status = await streamInfo(channel)
                    ytchan = await channelInfo(channel)
                    if len(stext) + len(f'{ytchan["name"]}: <:green_circle:786380003306111018>\n') <= 2000:
                        if status["isLive"]:
                            stext += f'{ytchan["name"]}: <:green_circle:786380003306111018>\n'
                        else:
                            stext += f'{ytchan["name"]}: <:red_circle:786380003306111018>\n'
                    else:
                        if status["isLive"]:
                            stext2 += f'{ytchan["name"]}: <:green_circle:786380003306111018>\n'
                        else:
                            stext2 += f'{ytchan["name"]}: <:red_circle:786380003306111018>\n'
                break
            except Exception as e:
                if x == 2:
                    logging.error("An error has occured!", exc_info=True)
                    print("An error has occurred.")
                    traceback.print_tb(e)
                    if len(stext) + len(f'{channel}: <:warning:786380003306111018>\n') <= 2000:
                        stext += f'{channel}: <:warning:786380003306111018>\n'
                    else:
                        stext2 += f'{channel}: <:warning:786380003306111018>\n'
    await ctx.send(stext.strip())
    await ctx.send(stext2.strip())"""

async def streamNotify(bot, cData):
    with open("data/servers.json", encoding="utf-8") as f:
        servers = json.load(f)
    for server in servers:
        for channel in servers[server]:
            for ytch in cData:
                if ytch not in servers[server][channel]["notified"] and ytch in servers[server][channel]["livestream"]:
                    servers[server][channel]["notified"][ytch] = {
                        "videoId": ""
                    }
                if ytch in servers[server][channel]["livestream"] and cData[ytch]["videoId"] != servers[server][channel]["notified"][ytch]["videoId"]:
                    try:
                        whurl = await getwebhook(bot, servers, server, channel)
                        async with aiohttp.ClientSession() as session:
                            embed = discord.Embed(title=f'{cData[ytch]["videoTitle"]}', url=f'https://youtube.com/watch?v={cData[ytch]["videoId"]}')
                            embed.description = f'Started streaming {cData[ytch]["timeText"]}'
                            embed.set_image(url=cData[ytch]["thumbURL"])
                            webhook = Webhook.from_url(whurl, adapter=AsyncWebhookAdapter(session))
                            await webhook.send(f'New livestream from {cData[ytch]["name"]}!', embed=embed, username=cData[ytch]["name"], avatar_url=cData[ytch]["image"])
                    except Exception as e:
                        logging.error(f"Stream - An error has occurred while publishing stream notification to {channel}!", exc_info=True)
                        break
                    servers[server][channel]["notified"][ytch]["videoId"] = cData[ytch]["videoId"]
    with open("data/servers.json", "w", encoding="utf-8") as f:
        servers = json.dump(servers, f, indent=4)

async def streamClean(cData):
    with open("data/servers.json", encoding="utf-8") as f:
        servers = json.load(f)
    livech = []
    for ytch in cData:
        livech.append(ytch)
    for server in servers:
        for channel in servers[server]:
            for ytch in servers[server][channel]["notified"]:
                if ytch not in livech:
                    servers[server][channel]["notified"].remove(ytch)
    with open("data/servers.json", "w", encoding="utf-8") as f:
        servers = json.dump(servers, f, indent=4)

def scWrapper():
    return asyncio.run(streamcheck(loop=True))

class StreamCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=3.0)
    async def timecheck(self):
        logging.info("Starting stream checks.")
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                loop = asyncio.get_running_loop()
                cData = await loop.run_in_executor(pool, scWrapper)
            logging.info("Stream - Notifying channels.")
            await streamNotify(self.bot, cData)
        except Exception as e:
            logging.error("Stream - An error has occurred in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.info("Stream checks done.")