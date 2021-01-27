import aiohttp, discord, asyncio, json, yaml, logging, sys, imgkit, os, pytz, traceback
from datetime import datetime
from discord.ext.commands.core import command
from itertools import islice
from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands, tasks
from infoscraper import streamInfo, channelInfo

with open("data/settings.yaml") as f:
    settings = yaml.load(f, Loader=yaml.FullLoader)

if settings["logging"] == "info":
    logging.basicConfig(level=logging.INFO, filename='status.log', filemode='w', format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
elif settings["logging"] == "debug":
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.FileHandler('status.log', 'w', 'utf-8')], format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')

bot = commands.Bot(command_prefix=commands.when_mentioned_or(settings["prefix"]), help_command=None)
bot.remove_command('help')

def chunks(data, SIZE=10000):
    it = iter(data)
    for i in range(0, len(data), SIZE):
        yield {k:data[k] for k in islice(it, SIZE)}

def creatorCheck(ctx):
    return ctx.author.id == 256009740239241216

def subPerms(ctx):
    userPerms = ctx.channel.permissions_for(ctx.author)
    return userPerms.administrator or userPerms.manage_webhooks or ctx.guild.owner_id == ctx.author.id

async def subCheck(ctx, subMsg, mode, chName):
    if mode == 1:
        action = "Subscribe"
    elif mode == 2:
        action = "Unsubscribe"
    else:
        return {
            "success": False
        }
    
    subEmbed = discord.Embed(title=chName, description=f"{action} to the channel's:\n\n"
                                                        "1. Livestream Notifications\n2. Milestone Notifications\n3. Both\n\n"
                                                        "X. Cancel\n\n[Bypass this by setting the channel's default subscription type using `y!subdefault`]")
    
    if mode == 2:
        subEmbed.description=f"Unsubscribe to channel with subscription type:\n\n" \
                              "1. Livestream Notifications\n2. Milestone Notifications\n3. Both\n\n" \
                              "X. Cancel\n\n[Bypass this by setting the channel's default subscription type using `y!subdefault`]"

    await subMsg.edit(content=None, embed=subEmbed)

    uInput = {
        "success": False
    }

    def check(m):
        return m.content.lower() in ['1', '2', '3', 'x'] and m.author == ctx.author

    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await subMsg.delete()
            break
        else:
            if msg.content in ['1', '2', '3']:
                await msg.delete()
                if msg.content == '1':
                    uInput["subType"] = ["livestream"]
                elif msg.content == '2':
                    uInput["subType"] = ["milestone"]
                elif msg.content == '3':
                    uInput["subType"] = ["livestream", "milestone"]
                uInput["success"] = True
                break
            elif msg.content.lower() == 'x':
                await msg.delete()
                break
            else:
                await msg.delete()
    
    return uInput

async def getSubType(ctx, mode, prompt = None):
    pEmbed = discord.Embed()

    if mode == 1:
        pEmbed.title = "Default Channel Subscription Type"
        pEmbed.description = "Set this to:\n\n1. Livestream Notifications\n2. Milestone Notifications\n" \
                             "3. Both\n\nX. Cancel"
        def check(m):
            return m.content.lower() in ['1', '2', '3', 'x'] and m.author == ctx.author
        prompt = await ctx.send(embed=pEmbed)
    elif mode == 2:
        pEmbed.title = "Channel Subscription Type"
        pEmbed.description = "Get subscription list for:\n\n1. Livestream Notifications\n" \
                             "2. Milestone Notifications\n\nX. Cancel" \
                             "\n\n[Bypass this by setting the channel's default subscription type using `y!subdefault`]"
        def check(m):
            return m.content.lower() in ['1', '2', 'x'] and m.author == ctx.author  
        await prompt.edit(content=None, embed=pEmbed)

    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await prompt.delete()
            await ctx.message.delete()
            return {
                "success": False
            }
        else:
            if msg.content in ['1', '2', '3']:
                subTypes = ["livestream", "milestone"]
                if mode == 1:
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    if msg.content != '3':
                        subType = [subTypes[int(msg.content) - 1]]
                        subText = subTypes[int(msg.content) - 1]
                    else:
                        subType = subTypes
                        subText = "both"
                    try:
                        servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"] = subType
                    except:
                        servers = await genServer(servers, ctx.guild, ctx.channel)
                        servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"] = subType
                    with open("data/servers.json", "w") as f:
                        json.dump(servers, f, indent=4)

                    await msg.delete()
                    await ctx.message.delete()
                    await prompt.edit(content=f"This channel will now subscribe to {subText} notifications by default.", embed=None)
                    break
                elif mode == 2 and msg.content in ['1', '2']:
                    await msg.delete()
                    return {
                        "success": True,
                        "subType": subTypes[int(msg.content) - 1]
                    }
                else:
                    await msg.delete()
            elif msg.content.lower() == 'x':
                await msg.delete()
                await prompt.delete()
                await ctx.message.delete()
                return {
                    "success": False
                }
            else:
                await msg.delete()

async def botError(ctx, error):
    errEmbed = discord.Embed(title="An error has occurred!", color=discord.Colour.red())
    if "403 Forbidden" in str(error):
        permData = [{
            "formatName": "Manage Webhooks",
            "dataName": "manage_webhooks"
        }, {
            "formatName": "Manage Messages",
            "dataName": "manage_messages"
        }]
        permOutput = []
        for perm in iter(ctx.guild.me.permissions_in(ctx.channel)):
            for pCheck in permData:
                if perm[0] == pCheck["dataName"]:
                    if not perm[1]:
                        permOutput.append(pCheck["formatName"])
        plural = "this permission"
        if len(permOutput) > 1:
            plural = "these permissions"
        errEmbed.description = "This bot has insufficient permissions for this channel.\n" \
                               f"Please allow the bot {plural}:\n"
        for perm in permOutput:
            errEmbed.description += f'\n - `{perm}`'
        
        return errEmbed
    elif isinstance(error, commands.CheckFailure):
        errEmbed.description = "You are missing permissions to use this bot.\n" \
                               "Ensure that you have one of these permissions for the channel/server:\n\n" \
                               " - `Administrator (Server)`\n - `Manage Webhooks (Channel/Server)`"
        
        return errEmbed
    else:
        print("An unknown error has occurred.")
        traceback.print_tb(error.__traceback__)
        print(error)

async def genServer(servers, cserver, cchannel):
    if str(cserver.id) not in servers:
        logging.debug("New server! Adding to database.")
        servers[str(cserver.id)] = {
            str(cchannel.id): {
                "url": "",
                "notified": {},
                "livestream": [],
                "milestone": []
            }
        }
    elif str(cchannel.id) not in servers[str(cserver.id)]:
        logging.debug("New channel in server! Adding to database.")
        servers[str(cserver.id)][str(cchannel.id)] = {
            "url": "",
            "notified": {},
            "livestream": [],
            "milestone": []
        }
    
    return servers

async def getwebhook(servers, cserver, cchannel):
    if isinstance(cserver, str) and isinstance(cchannel, str):
        cserver = bot.get_guild(int(cserver))
        cchannel = bot.get_channel(int(cchannel))
    try:
        logging.debug(f"Trying to get webhook url for {cserver.id}")
        whurl = servers[str(cserver.id)][str(cchannel.id)]["url"]
    except KeyError:
        logging.debug("Failed to get webhook url! Creating new webhook.")
        servers = await genServer(servers, cserver, cchannel)
        with open("yagoo.jpg", "rb") as image:
            webhook = await cchannel.create_webhook(name="Yagoo", avatar=image.read())
        whurl = webhook.url
        servers[str(cserver.id)][str(cchannel.id)]["url"] = whurl
        with open("data/servers.json", "w") as f:
            json.dump(servers, f, indent=4)
    return whurl

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

async def streamNotify(cData):
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
                    whurl = await getwebhook(servers, server, channel)
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
    def __init__(self):
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=3.0)
    async def timecheck(self):
        logging.info("Starting stream checks.")
        cData = await streamcheck(loop=True)
        logging.info("Notifying channels (Stream).")
        await streamNotify(cData)
        logging.info("Stream checks done.")

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
            except:
                if x == 2:
                    logging.error(f'Milestone - Unable to get info for {channel}!')
                    break
                else:
                    logging.warning(f'Milestone - Failed to get info for {channel}. Retrying...')
    
    if not noWrite:
        with open("data/channels.json", "w") as f:
            json.dump(channels, f, indent=4)
    
    return milestone

async def milestoneNotify(msDict):
    logging.debug(f'Milestone Data: {msDict}')
    with open("data/servers.json") as f:
        servers = json.load(f)
    for channel in msDict:
        logging.debug(f'Generating milestone image for id {channel}')
        with open("milestone/milestone.html") as f:
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
    def __init__(self):
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=3.0)
    async def timecheck(self):
        logging.info("Starting milestone checks.")
        msData = await milestoneCheck()
        if msData != {}:
            logging.info("Notifying channels (Milestone).")
            await milestoneNotify(msData)
        logging.info("Milestone checks done.")

async def bdayCheck():
    update = False
    write = False
    bdayResults = {}

    with open("data/bot.json") as f:
        bdata = json.load(f)
    
    if "bdayCheck" not in bdata:
        bdata["bdayCheck"] = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%m%d")
        write = True

    now = datetime.now(pytz.timezone("Asia/Tokyo")).replace(hour=0, minute=0, second=0, microsecond=0)
    if pytz.timezone("Asia/Tokyo").localize(datetime.strptime(bdata["bdayCheck"], "%m%d").replace(year=datetime.now(pytz.timezone("Asia/Tokyo")).year)) < now:
        with open("data/birthdays.json") as f:
            bdays = json.load(f)

        if str(now.day) in bdays[str(now.month)]:
            bdayCurrent = bdays[str(now.month)][str(now.day)]
            update = True
        
        bdata["bdayCheck"] = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%m%d")
        write = True
    
    if write:
        with open("data/bot.json") as f:
            json.dump(bdata, f)
    
    if update:
        return {
            "occurToday": update,
            "bdayData": bdayCurrent
        }
    else:
        return {
            "occurToday": update
        }

@bot.event
async def on_ready():
    print("Yagoo Bot now streaming!")
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name='other Hololive members'))
    if settings["notify"]:
        bot.add_cog(StreamCycle())
    if settings["milestone"]:
        bot.add_cog(msCycle())

@bot.event
async def on_guild_remove(server):
    logging.info(f'Got removed from a server, cleaning up server data for: {str(server)}')
    with open("data/servers.json") as f:
        servers = json.load(f)
    servers.pop(str(server.id), None)
    with open("data/servers.json", "w") as f:
        json.dump(servers, f, indent=4)

@bot.command(alias=['h'])
async def help(ctx):
    hembed = discord.Embed(title="Yagoo Bot Commands")
    hembed.description = "Currently the bot only has a small number of commands, as it is still in development!\n" \
                         "New stream notifications will be posted on a 3 minute interval, thus any new notifications " \
                         "will not come immediately after subscribing.\n" \
                         "Currently all the commands require the user to have either the `Administrator` or `Manage Webhook` permission in the channel or server."
    
    hembed.add_field(name="Commands",
                     value="**y!sub** (Alias: subscribe)\n"
                           "Brings up a list of channels to subscribe to.\n\n"
                           "**y!unsub** (Alias: unsubscribe)\n"
                           "Brings up a list of channels to unsubscribe to.\n\n"
                           "**y!sublist** (Alias: subs, subslist)\n"
                           "Brings up a list of channels that the current chat channel has subscribed to.\n\n"
                           "**y!subdefault** (Alias: subDefault)\n"
                           "Set's the default subscription type for the channel.")

    await ctx.send(embed=hembed)

@bot.command(aliases=['subdefault'])
@commands.check(subPerms)
async def subDefault(ctx):
    await getSubType(ctx, 1)

@subDefault.error
async def subdef_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

# TODO: Error on missing perms (Manage Webhooks and Manage Messages) here
@bot.command(aliases=['sub'])
@commands.check(subPerms)
async def subscribe(ctx):
    listmsg = await ctx.send("Loading channels list...")

    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    csplit = []
    for split in chunks(channels, 9):
        csplit.append(split)
    first = True
    pagepos = 0
    picknum = 1
    pickstr = ""
    picklist = []
    for split in csplit[pagepos]:
        ytch = csplit[pagepos][split]
        pickstr += f'{picknum}. {ytch["name"]}\n'
        picklist.append(split)
        picknum += 1
    if pagepos == 0:
        pickstr += f'\nA. Subscribe to all channels\nN. Go to next page\nX. Cancel'
    elif pagepos == len(csplit) - 1:
        pickstr += f'\nA. Subscribe to all channels\nB. Go to previous page\nX. Cancel'
    else:
        pickstr += f'\nA. Subscribe to all channels\nN. Go to next page\nB. Go to previous page\nX. Cancel'

    listembed = discord.Embed(title="Subscribe to channel:", description=pickstr)
    await listmsg.edit(content=None, embed=listembed)

    while True:
        if not first:
            picknum = 1
            pickstr = ""
            picklist = []
            for split in csplit[pagepos]:
                ytch = csplit[pagepos][split]
                pickstr += f'{picknum}. {ytch["name"]}\n'
                picklist.append(split)
                picknum += 1
            if pagepos == 0:
                pickstr += f'\nA. Subscribe to all channels\nN. Go to next page\nX. Cancel'
            elif pagepos == len(csplit) - 1:
                pickstr += f'\nA. Subscribe to all channels\nB. Go to previous page\nX. Cancel'
            else:
                pickstr += f'\nA. Subscribe to all channels\nN. Go to next page\nB. Go to previous page\nX. Cancel'

            listembed = discord.Embed(title="Subscribe to channel:", description=pickstr)
            await listmsg.edit(embed=listembed)
        else:
            first = False

        def check(m):
            return m.content.lower() in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'n', 'b', 'x'] and m.author == ctx.author

        while True:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await listmsg.delete()
                await ctx.message.delete()
                return
            else:
                if msg.content in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await getwebhook(servers, ctx.guild, ctx.channel)
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await msg.delete()
                    if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
                        uInput = await subCheck(ctx, listmsg, 1, csplit[pagepos][picklist[int(msg.content) - 1]]["name"])
                    else:
                        uInput = {
                            "success": True,
                            "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
                        }
                    lastSubbed = False

                    if not uInput["success"]:
                        await listmsg.delete()
                        await ctx.message.delete()
                        return

                    for subType in uInput["subType"]:
                        if picklist[int(msg.content) - 1] not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(picklist[int(msg.content) - 1])
                        else:
                            if len(uInput["subType"]) > 1 and not lastSubbed:
                                lastSubbed = True
                            else:
                                ytch = csplit[pagepos][picklist[int(msg.content) - 1]]
                                await listmsg.edit(content=f'This channel is already subscribed to {ytch["name"]}.', embed=None)
                                await ctx.message.delete()
                                return
                    with open("data/servers.json", "w") as f:
                        json.dump(servers, f, indent=4)
                    ytch = csplit[pagepos][picklist[int(msg.content) - 1]]
                    await listmsg.edit(content=f'This channel is now subscribed to: {ytch["name"]}.', embed=None)
                    await ctx.message.delete()
                    return
                elif msg.content.lower() == 'a':
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await getwebhook(servers, ctx.guild, ctx.channel)
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await msg.delete()
                    if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
                        uInput = await subCheck(ctx, listmsg, 1, "Subscribing to all channels.")
                    else:
                        uInput = {
                            "success": True,
                            "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
                        }
                    if not uInput["success"]:
                        await listmsg.delete()
                        await ctx.message.delete()
                        return
                    for subType in uInput["subType"]:
                        for ytch in channels:
                            if ytch not in servers[str(ctx.guild.id)][str(ctx.channel.id)][subType]:
                                servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].append(ytch)
                    with open("data/servers.json", "w") as f:
                        json.dump(servers, f, indent=4)
                    await listmsg.edit(content=f'This channel is now subscribed to all Hololive YouTube channels.', embed=None)
                    await ctx.message.delete()
                    return
                elif msg.content.lower() == 'n' and pagepos < len(csplit) - 1:
                    await msg.delete()
                    pagepos += 1
                    break
                elif msg.content.lower() == 'b' and pagepos > 0:
                    await msg.delete()
                    pagepos -= 1
                    break
                elif msg.content.lower() == 'x':
                    await msg.delete()
                    await listmsg.delete()
                    await ctx.message.delete()
                    return
                else:
                    await msg.delete()

@subscribe.error
async def sub_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

# TODO: Error on missing perms (Manage Webhooks and Manage Messages) here
@bot.command(aliases=["unsub"])
@commands.check(subPerms)
async def unsubscribe(ctx):
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    with open("data/servers.json") as f:
        servers = json.load(f)
    
    unsubmsg = await ctx.send("Loading subscription list...")

    if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
        uInput = await subCheck(ctx, unsubmsg, 2, "Unsubscribe")
    else:
        uInput = {
            "success": True,
            "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]
        }
    
    if not uInput["success"]:
        await unsubmsg.delete()
        await ctx.message.delete()
        return
    
    if len(uInput["subType"]) > 1:
        subDisp = "livestream"
    else:
        subDisp = uInput["subType"][0]
    
    try:
        len(servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp])
    except:
        await unsubmsg.edit(content="There are no subscriptions on this channel.", embed=None)
        return

    multi = False
    sublist = []
    templist = []
    if len(servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]) > 9:
        for sub in servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]:
            if len(templist) < 9:
                templist.append(sub)
            else:
                sublist.append(templist)
                templist = [sub]
        sublist.append(templist)
        multi = True
    elif len(servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]) > 0 and len(servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]) < 10:
        for sub in servers[str(ctx.guild.id)][str(ctx.channel.id)][subDisp]:
            sublist.append(sub)
    else:
        await unsubmsg.edit(content="There are no subscriptions on this channel.", embed=None)
        return
    
    pagepos = 0
    while True:
        dispstring = ""
        dispnum = 1
        if multi:
            subProc = sublist[pagepos]
            for sub in subProc:
                ytch = channels[sub]
                dispstring += f'{dispnum}. {ytch["name"]}\n'
                dispnum += 1
            if pagepos == 0:
                dispstring += f'\nA. Unsubscribe to all channels\nN. Go to next page\nX. Cancel'
            elif pagepos == len(sublist) - 1:
                dispstring += f'\nA. Unsubscribe to all channels\nB. Go to previous page\nX. Cancel'
            else:
                dispstring += f'\nA. Unsubscribe to all channels\nN. Go to next page\nB. Go to previous page\nX. Cancel'
        else:
            subProc = sublist
            for sub in sublist:
                ytch = channels[sub]
                dispstring += f'{dispnum}. {ytch["name"]}\n'
                dispnum += 1
            dispstring += f'A. Unsubscribe to all channels\nX. Cancel'
        
        usembed = discord.Embed(title="Unsubscribe from channel:", description=dispstring)
        await unsubmsg.edit(content=None, embed=usembed)

        def check(m):
            return m.content.lower() in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'n', 'b', 'x'] and m.author == ctx.author

        while True:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await unsubmsg.delete()
                await ctx.message.delete()
                return
            else:
                if msg.content in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await getwebhook(servers, ctx.guild, ctx.channel)
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await msg.delete()
                    for subType in uInput["subType"]:
                        try:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)][subType].remove(subProc[int(msg.content) - 1])
                        except:
                            ytch = channels[subProc[int(msg.content) - 1]]
                            await unsubmsg.edit(content=f'Couldn\'t unsubscribe {subType} notifications from: {ytch["name"]}!', embed=None)
                        else:
                            servers[str(ctx.guild.id)][str(ctx.channel.id)]["notified"].pop(subProc[int(msg.content) - 1], None)
                            ytch = channels[subProc[int(msg.content) - 1]]
                            await unsubmsg.edit(content=f'Unsubscribed from: {ytch["name"]}.', embed=None)
                    with open("data/servers.json", "w") as f:
                        json.dump(servers, f, indent=4)
                    await ctx.message.delete()
                    return
                elif msg.content.lower() == 'a':
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    await getwebhook(servers, ctx.guild, ctx.channel)
                    with open("data/servers.json") as f:
                        servers = json.load(f)
                    for subType in uInput["subType"]:
                        servers[str(ctx.guild.id)][str(ctx.channel.id)][subType] = []
                    servers[str(ctx.guild.id)][str(ctx.channel.id)]["notified"] = {}
                    with open("data/servers.json", "w") as f:
                        json.dump(servers, f, indent=4)
                    await unsubmsg.edit(content=f'This channel is now unsubscribed from any Hololive YouTube channels.', embed=None)
                    await msg.delete()
                    await ctx.message.delete()
                    return
                elif multi:
                    if msg.content.lower() == 'n' and pagepos < len(sublist) - 1:
                        await msg.delete()
                        pagepos += 1
                        break
                    elif msg.content.lower() == 'b' and pagepos > 0:
                        await msg.delete()
                        pagepos -= 1
                        break
                elif msg.content.lower() == 'x':
                    await msg.delete()
                    await unsubmsg.delete()
                    await ctx.message.delete()
                    return
                else:
                    await msg.delete()

@unsubscribe.error
async def unsub_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

# TODO: Error on missing perms (Manage Messages) here
@bot.command(aliases=["subs", "subslist", "subscriptions", "subscribed"])
@commands.check(subPerms)
async def sublist(ctx):
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    with open("data/servers.json") as f:
        servers = json.load(f)
    
    subsmsg = await ctx.send("Loading subscription list...")

    if "subDefault" not in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
        uInput = await getSubType(ctx, 2, subsmsg)
    else:
        if not len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) > 1:
            uInput = {
                "success": True,
                "subType": servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"][0]
            }
        else:
            uInput = {
                "success": True,
                "subType": "livestream"
            }

    if not uInput["success"]:
        return
    
    try:
        len(servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]])
    except:
        await subsmsg.edit(content="There are no subscriptions on this channel.", embed=None)
        return

    multi = False
    sublist = []
    templist = []
    if len(servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]) > 10:
        for sub in servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]:
            if len(templist) < 10:
                templist.append(sub)
            else:
                sublist.append(templist)
                templist = [sub]
        sublist.append(templist)
        multi = True
    elif len(servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]) > 0 and len(servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]) < 11:
        for sub in servers[str(ctx.guild.id)][str(ctx.channel.id)][uInput["subType"]]:
            sublist.append(sub)
    else:
        await subsmsg.edit(content="There are no subscriptions on this channel.", embed=None)
        return
    
    pagepos = 0
    realnum = 1
    while True:
        dispstring = ""
        if multi:
            subProc = sublist[pagepos]
            for sub in subProc:
                ytch = channels[sub]
                dispstring += f'{realnum}. {ytch["name"]}\n'
                realnum += 1
            if pagepos == 0:
                dispstring += f'\nN. Go to next page\nX. Remove this message'
            elif pagepos == len(sublist) - 1:
                dispstring += f'\nB. Go to previous page\nX. Remove this message'
            else:
                dispstring += f'\nN. Go to next page\nB. Go to previous page\nX. Remove this message'
        else:
            subProc = sublist
            for sub in sublist:
                ytch = channels[sub]
                dispstring += f'{realnum}. {ytch["name"]}\n'
                realnum += 1
            dispstring += f'\nX. Remove this message'
        
        subsembed = discord.Embed(title="Currently subscribed channels:", description=dispstring)
        await subsmsg.edit(content=None, embed=subsembed)

        def check(m):
            return m.content.lower() in ['n', 'b', 'x'] and m.author == ctx.author

        while True:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                return
            else:
                if msg.content.lower() == 'x':
                    await msg.delete()
                    await subsmsg.delete()
                    await ctx.message.delete()
                    return
                elif multi:
                    if msg.content.lower() == 'n' and pagepos < len(sublist) - 1:
                        await msg.delete()
                        pagepos += 1
                        break
                    elif msg.content.lower() == 'b' and pagepos > 0:
                        await msg.delete()
                        pagepos -= 1
                        realnum -= 20
                        break
                else:
                    await msg.delete()

@sublist.error
async def sublist_error(ctx, error):
    errEmbed = await botError(ctx, error)
    if errEmbed:
        await ctx.send(embed=errEmbed)

@bot.command()
@commands.check(creatorCheck)
async def test(ctx):
    await ctx.send("Rushia Ch. \u6f64\u7fbd\u308b\u3057\u3042")

@bot.command(aliases=["livestats", "livestat"])
@commands.check(subPerms)
async def livestatus(ctx):
    loadmsg = await ctx.send("Loading info...")
    await streamcheck(ctx, True)
    await loadmsg.delete()

@bot.command()
@commands.check(creatorCheck)
async def mscheck(ctx, vtuber):
    with open("data/channels.json") as f:
        channels = json.load(f)

    ytch = await channelInfo(vtuber)
    if ytch["roundSubs"] < 1000000:
        subtext = f'{int(ytch["roundSubs"] / 1000)}K Subscribers'
    else:
        if ytch["roundSubs"] == ytch["roundSubs"] - (ytch["roundSubs"] % 1000000):
            subtext = f'{int(ytch["roundSubs"] / 1000000)}M Subscribers'
        else:
            subtext = f'{ytch["roundSubs"] / 1000000}M Subscribers'
    msDict = {
        vtuber: {
            "name": ytch["name"],
            "image": ytch["image"],
            "banner": ytch["mbanner"],
            "msText": subtext
        }
    }
    await milestoneNotify(msDict)
    await ctx.send(file=discord.File(f'milestone/generated/{vtuber}.png'))

@bot.command()
@commands.check(creatorCheck)
async def nstest(ctx):
    with open("data/servers.json") as f:
        servers = json.load(f)
    
    live = await streamcheck()
    whurl = await getwebhook(servers, ctx.guild, ctx.channel)

    for livech in live:
        async with aiohttp.ClientSession() as session:
            embed = discord.Embed(title=f'{live[livech]["videoTitle"]}', url=f'https://youtube.com/watch?v={live[livech]["videoId"]}')
            embed.description = f'Started streaming {live[livech]["timeText"]}'
            embed.set_image(url=f'https://img.youtube.com/vi/{live[livech]["videoId"]}/maxresdefault.jpg')
            webhook = Webhook.from_url(whurl, adapter=AsyncWebhookAdapter(session))
            await webhook.send(f'New livestream from {live[livech]["name"]}!', embed=embed, username=live[livech]["name"], avatar_url=live[livech]["image"])

@bot.command()
@commands.check(creatorCheck)
async def postas(ctx, vtuber, *, text):
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    with open("data/servers.json") as f:
        servers = json.load(f)
    whurl = await getwebhook(servers, ctx.guild, ctx.channel)
    ytch = await channelInfo(channels[vtuber]["channel"])
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(whurl, adapter=AsyncWebhookAdapter(session))
        await webhook.send(text, username=ytch["name"], avatar_url=ytch["image"])

@bot.command(aliases=["maint", "shutdown", "stop"])
@commands.check(creatorCheck)
async def maintenance(ctx):
    await ctx.send("Changing to maintenance mode...\nBot will shut down in 5 minutes.")
    logging.info("Maintenance mode started. Shutting down in 5 minutes.")
    ctdwn = ["5 minutes", "4 minutes", "3 minutes", "2 minutes", "1 minute"]
    for x in range(5):
        if x != 4:
            await bot.change_presence(status=discord.Status.idle, activity=discord.Activity(type=discord.ActivityType.playing, name=f'Bot will undergo maintenance in {ctdwn[x]}.'))
        else:
            await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.playing, name=f'Bot will undergo maintenance in {ctdwn[x]}.'))
        await asyncio.sleep(60)
    logging.info("Shutting down!")
    await bot.change_presence(status=discord.Status.offline)
    bot.remove_cog(StreamCycle())
    bot.remove_cog(msCycle())
    logging.info("Stopped Stream Checker.")
    dev = bot.get_user(256009740239241216)
    await dev.send("Bot has shutdown.")
    await bot.close()
    logging.info("Logged out.")
    sys.exit()

bot.run(settings["token"])
