import json
import asyncio
import logging
import discord
from .dataWrite import genServer

async def getSubType(ctx, mode, bot, prompt = None):
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
                    except KeyError:
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

async def getwebhook(bot, servers, cserver, cchannel):
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
