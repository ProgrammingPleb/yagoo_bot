import discord
import json
import asyncio
import tweepy
from typing import Union
from discord.ext import commands
from discord_slash.context import SlashContext
from discord_components import Button, ButtonStyle
from ..infoscraper import FandomScrape, TwitterScrape
from ..share.botUtils import TwitterUtils, embedContinue, msgDelete, fandomTextParse, vtuberSearch
from ..share.prompts import TwitterPrompts, botError

async def botHelp():
    hembed = discord.Embed(title="Yagoo Bot Commands")
    hembed.description = "Currently the bot only has a small number of commands, as it is still in development!\n" \
                         "New stream notifications will be posted on a 3 minute interval, thus any new notifications " \
                         "will not come immediately after subscribing.\n" \
                         "Currently all the commands (except for `y!help` and `y!info`) require the user to have either the `Administrator` or `Manage Webhook` permission in the channel or server.\n" \
                         "Anything in angle brackets `<>` are required, leaving them will result in an error." \
                         "Meanwhile, anything in square brackets `[]` are optional, so leaving them will also make the command work."
    
    hembed.add_field(name="Commands",
                     value="**y!sub** [VTuber Name] (Alias: subscribe)\n"
                           "Brings up a list of channels to subscribe to.\n"
                           "Add a non-Hololive VTuber's name to the command to opt in to their notifications.\n\n"
                           "**y!unsub** (Alias: unsubscribe)\n"
                           "Brings up a list of channels to unsubscribe to.\n\n"
                           "**y!sublist** (Alias: subs, subslist)\n"
                           "Brings up a list of channels that the current chat channel has subscribed to.\n\n"
                           "**y!subdefault** (Alias: subDefault)\n"
                           "Set's the default subscription type for the channel.\n\n"
                           "**y!info** <VTuber Name> (Alias: getinfo)\n"
                           "Gets information about a VTuber.",
                     inline=False)
    
    hembed.add_field(name="Issues/Suggestions?",
                     value="If you run into any problems with/have any suggestions for the bot, then feel free to join the [support server](https://discord.gg/GJd6sdNjeQ) and drop a message there.",
                     inline=False)

    return hembed

async def botGetInfo(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, name: str):
    retry = True
    infoMsg = None

    while retry:
        fandomName = (await FandomScrape.searchChannel(name, True))["name"]
        fullPage = await FandomScrape.getChannel(fandomName, dataKey="text")
        allSections = await FandomScrape.getSections(fullPage)
        allSData = await FandomScrape.getSectionData(fullPage, allSections)
        infoEmbed, excessParts = await fandomTextParse.parseToEmbed(fandomName, allSData)
        infoEmbed.set_thumbnail(url=await FandomScrape.getThumbnail(fullPage))

        if infoMsg is None:
            infoMsg = await ctx.send(embed=infoEmbed)
        else:
            await infoMsg.edit(embed=infoEmbed)

        if excessParts == None:
            return

        excessChoice = []
        for part in excessParts:
            excessChoice.append(part.lower())
        
        def check(m):
            return m.content.lower() in excessChoice + ['search'] and m.author == ctx.author

        excessLoop = True
        while excessLoop:
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                retry = False
                break
            await msg.delete()
            if msg.content.lower() == 'search':
                chChoice = await vtuberSearch(ctx, bot, name, infoMsg, "Get info for", True)
                if chChoice["success"]:
                    name = chChoice["name"]
                    excessLoop = False
                    retry = True
                else:
                    await infoMsg.edit(embed=infoEmbed)
            else:
                for part in excessParts:
                    if msg.content.lower() == part.lower():
                        userReturn = await embedContinue(ctx, bot, infoMsg, part, excessParts[part], fandomName)
                        if userReturn:
                            await infoMsg.edit(embed=infoEmbed)
                            break
                        else:
                            excessLoop = False

# Tasklist:
# Create disclaimer on core unsubscribe command
# TODO: SQL rewrite
# TODO: Move to it's own file if possible
# TODO: Ensure that the channel has a webhook first
class botTwt:
    async def follow(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, accLink: str):
        twtHandle = ""

        if accLink == "":
            return await ctx.send(embed=await botError(ctx, "No Twitter ID"))
        
        with open("data/twitter.json") as f:
            twtData = json.load(f)
        
        twtHandle = await TwitterUtils.getScreenName(accLink)
        
        try:
            twtUser = await TwitterScrape.getUserDetails(twtHandle)
        except tweepy.NotFound as e:
            return await ctx.send(embed=await botError(ctx, e))

        if "custom" not in twtData:
            twtData["custom"] = {}
        twtEmbed = discord.Embed(title=f"Following {twtUser.name} to this channel", description="Are you sure to subscribe to this Twitter account?")
        twtMsg = await ctx.send(embed=twtEmbed, components=[[Button(label="No", style=ButtonStyle.red), Button(label="Yes", style=ButtonStyle.blue)]])
        
        def check(res):
            return res.user == ctx.message.author and res.channel == ctx.channel
        
        try:
            res = await bot.wait_for('button_click', check=check, timeout=60)
        except asyncio.TimeoutError:
            await twtMsg.delete()
            await msgDelete(ctx)
            return
        if res.component.label == "Yes":
            dbExist = await TwitterUtils.dbExists(twtUser.id_str)
            if not dbExist["status"]:
                twtData = await TwitterUtils.newAccount(twtUser)
            status = await TwitterUtils.followActions("add", str(ctx.guild.id), str(ctx.channel.id), twtUser.id_str)
            if not status:
                await twtMsg.edit(content=f"This channel is already following @{twtUser.name}'s tweets.", embed=" ", components=[])
            else:
                await twtMsg.edit(content=f"This channel is now following @{twtUser.name}'s tweets.", embed=" ", components=[])
            await msgDelete(ctx)
            return
        else:
            await twtMsg.delete()
            await msgDelete(ctx)
            return
    
    async def unfollow(ctx: commands.Context, bot: commands.Bot):
        twtMsg = await ctx.send("Loading custom Twitter accounts.")

        with open("data/servers.json") as f:
            servers = json.load(f)
        
        with open("data/twitter.json") as f:
            twitter = json.load(f)
        
        await TwitterPrompts.unfollow(ctx, bot, twtMsg, twitter["custom"], servers)
