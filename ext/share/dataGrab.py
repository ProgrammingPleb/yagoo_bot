import json
import asyncio
import logging
import discord
from discord.ext import commands
from ext.share.prompts import botError
from .dataWrite import genServer
from ext.share.botUtils import msgDelete, serverSubTypes

async def getSubType(ctx: commands.Context, mode, bot: commands.Bot, prompt = None):
    pEmbed = discord.Embed()
    subDNum = 1
    subOptions = ["Livestream", "Milestone", "Premiere"]            # Update this on prompts.py/subCheck() and botUtils.py/getAllSubs() too
    subChoice = []

    with open("data/servers.json") as f:
        servers = json.load(f)

    if mode == 1:
        
        subEText = "Toggle:\n\n"
        if "subDefault" in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
            for subType in subOptions:
                if subType.lower() in servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]:
                    subEText += f"{subDNum}. {subType} Notifications 🟢\n"
                else:
                    subEText += f"{subDNum}. {subType} Notifications 🔴\n"
                subChoice.append(str(subDNum))
                subDNum += 1
        else:
            for subType in subOptions:
                subEText += f"{subDNum}. {subType} Notifications 🔴\n"
                subChoice.append(str(subDNum))
                subDNum += 1
        subEText += f"{subDNum}. All Notifications\nX. Cancel\n\n[Toggle multiple defaults by seperating them using commas, for example `1,3`.]"

        subChoice += [str(subDNum), 'x']

        pEmbed.title = "Default Channel Subscriptions"
        pEmbed.description = subEText
        def check(m):
            return (m.content.lower() in subChoice or ',' in m.content) and m.author == ctx.author
        prompt = await ctx.send(embed=pEmbed)
    elif mode == 2:
        subEText = "Get subscription list for:\n\n"

        valid = False
        actualSubTypes = []
        for serverKey in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
            if serverKey.capitalize() in subOptions:
                if servers[str(ctx.guild.id)][str(ctx.channel.id)][serverKey] != []:
                    actualSubTypes.append(serverKey.capitalize())
                    valid = True

        if not valid:
            await ctx.send(embed = await botError(ctx, "No Subscriptions"))
            return {
                "success": False
            }

        for subType in actualSubTypes:
            subEText += f"{subDNum}. {subType} Notifications\n"
            subChoice.append(str(subDNum))
            subDNum += 1
        subEText += "X. Cancel\n\n[Bypass this by setting the channel's default subscription type using `y!subdefault`.]"
        subChoice += ['x']

        pEmbed.title = "Channel Subscription Type"
        pEmbed.description = subEText
        def check(m):
            return m.content.lower() in subChoice and m.author == ctx.author
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
            await msg.delete()
            if (msg.content.lower() in subChoice or "," in msg.content) and 'x' not in msg.content.lower():
                if mode == 1:
                    subUChoice = await serverSubTypes(msg, subChoice, subOptions)

                    if subUChoice["success"]:
                        try:
                            for subUType in subUChoice["subType"]:
                                if subUType not in servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]:
                                    servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"].append(subUType)
                                else:
                                    servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"].remove(subUType)
                        except KeyError:
                            servers = await genServer(servers, ctx.guild, ctx.channel)
                            servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"] = subUChoice["subType"]
                        with open("data/servers.json", "w") as f:
                            json.dump(servers, f, indent=4)
                        
                        subText = ""
                        if len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) == 2:
                            subText = f"{servers[str(ctx.guild.id)][str(ctx.channel.id)]['subDefault'][0]} and {servers[str(ctx.guild.id)][str(ctx.channel.id)]['subDefault'][1]}"
                        elif len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) == len(subOptions):
                            subText = "all"
                        elif len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) == 1:
                            subText = servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"][0]
                        else:
                            subTypeCount = 1
                            for subUType in servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]:
                                if subTypeCount == len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]):
                                    subText += f"and {subUType}"
                                else:
                                    subText += f"{subUType}, "

                        await msgDelete(ctx)
                        if len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) == 0:
                            await prompt.edit(content=f"Subscription defaults for this channel has been removed.", embed=None)
                        else:
                            await prompt.edit(content=f"This channel will now subscribe to {subText} notifications by default.", embed=None)
                        break
                elif mode == 2:
                    if "," not in msg.content:
                        return {
                            "success": True,
                            "subType": actualSubTypes[int(msg.content) - 1].lower()
                        }
            elif msg.content.lower() == 'x':
                await prompt.delete()
                await ctx.message.delete()
                return {
                    "success": False
                }

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
