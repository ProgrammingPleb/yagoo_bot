import json, aiohttp, discord, logging
from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands, tasks
from ..infoscraper import streamInfo, channelInfo
from ..share.dataGrab import getwebhook

async def streamcheck(ctx = None, test: bool = False, loop: bool = False):
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    if not test:
        cstreams = {}
        for channel in channels:
            for x in range(2):
                try:
                    # print(f'Checking {cshrt["name"]}...')
                    if channel != "":
                        status = await streamInfo(channel)
                        ytchannel = await channelInfo(channel)
                        if status["isLive"]:
                            cstreams[channel] = {
                                "name": ytchannel["name"],
                                "image": ytchannel["image"],
                                "videoId": status["videoId"],
                                "videoTitle": status["videoTitle"],
                                "timeText": status["timeText"]
                            }
                    break
                except:
                    continue
        return cstreams
    else:
        stext = ""
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
                except:
                    if x == 2:
                        if len(stext) + len(f'{channel}: <:warning:786380003306111018>\n') <= 2000:
                            stext += f'{channel}: <:warning:786380003306111018>\n'
                        else:
                            stext2 += f'{channel}: <:warning:786380003306111018>\n'
        await ctx.send(stext.strip())
        await ctx.send(stext2.strip())

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
                    whurl = await getwebhook(bot, servers, server, channel)
                    async with aiohttp.ClientSession() as session:
                        embed = discord.Embed(title=f'{cData[ytch]["videoTitle"]}', url=f'https://youtube.com/watch?v={cData[ytch]["videoId"]}')
                        embed.description = f'Started streaming {cData[ytch]["timeText"]}'
                        embed.set_image(url=f'https://img.youtube.com/vi/{cData[ytch]["videoId"]}/maxresdefault.jpg')
                        webhook = Webhook.from_url(whurl, adapter=AsyncWebhookAdapter(session))
                        await webhook.send(f'New livestream from {cData[ytch]["name"]}!', embed=embed, username=cData[ytch]["name"], avatar_url=cData[ytch]["image"])
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
    
class StreamCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=3.0)
    async def timecheck(self):
        logging.info("Starting stream checks.")
        cData = await streamcheck(loop=True)
        logging.info("Notifying channels (Stream).")
        await streamNotify(self.bot, cData)
        logging.info("Stream checks done.")