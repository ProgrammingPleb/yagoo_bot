from discord.ext import commands
from discord_slash.context import SlashContext
from itertools import islice
from typing import Union

def chunks(data, SIZE=10000):
    it = iter(data)
    for i in range(0, len(data), SIZE):
        yield {k:data[k] for k in islice(it, SIZE)}

def creatorCheck(ctx):
    return ctx.author.id == 256009740239241216

def subPerms(ctx):
    userPerms = ctx.channel.permissions_for(ctx.author)
    return userPerms.administrator or userPerms.manage_webhooks or ctx.guild.owner_id == ctx.author.id

async def msgDelete(ctx: Union[commands.Context, SlashContext]):
    if type(ctx) != SlashContext:
        await ctx.message.delete()

async def vtuberSearch(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, searchTerm: str, searchMsg):
    getChannel = False

    if "https://www.youtube.com/channel/" in searchTerm:
        for part in searchTerm.split("/"):
            if 23 <= len(part) <= 25:
                if part[0] == "U":
                    channelID = part
                    getChannel = True
    
    if 23 <= len(searchTerm) <= 25:
        if searchTerm[0] == "U":
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://www.youtube.com/channel/{searchTerm}") as r:
                    if r.status == 200:
                        cInfo = await channelInfo(channelID)
                        if not cInfo["success"]:
                            cInfo = await channelInfo(channelID, True)
                        sConfirm = await searchConfirm(ctx, bot, cInfo["name"], searchMsg, f"Subscribe to {cInfo['name']}?", "Subscribe to this channel", "Choose another channel")
                        if sConfirm["success"]:
                            return {
                                "success": True,
                                "channelID": searchTerm,
                                "name": cInfo['name']
                            }
                        elif not sConfirm["success"] and not sConfirm["declined"]:
                            await searchTerm.delete()
                            await msgDelete(ctx)
                            return {
                                "success": False
                            }
    
    if not getChannel:
        fandomSearch = await FandomScrape.searchChannel(searchTerm)

        if fandomSearch["status"] == "Success":
            sConfirm = await searchConfirm(ctx, bot, fandomSearch["name"], searchMsg, f"Subscribe to {fandomSearch['name']}?", "Subscribe to this channel", "Choose another channel")
            if sConfirm["success"]:
                channelID = await FandomScrape.getChannelURL(fandomSearch["name"])
                channelID["name"] = fandomSearch["name"]
                return channelID
            elif not sConfirm["success"] and not sConfirm["declined"]:
                await searchMsg.delete()
                await msgDelete(ctx)
                return {
                    "success": False
                }
        
        if not getChannel or fandomSearch["status"] == "Cannot Match":
            sPick = await searchPrompt(ctx, bot, fandomSearch["results"], searchMsg, "Select a channel to subscribe to:")
            if not sPick["success"]:
                await searchMsg.delete()
                await msgDelete(ctx)
                return {
                    "success": False
                }
            channelID = await FandomScrape.getChannelURL(sPick["name"])
            channelID["name"] = sPick["name"]
            return channelID
