"""
This file is a part of Yagoo Bot <https://yagoo.pleb.moe/>
Copyright (C) 2020-present  ProgrammingPleb

Yagoo Bot is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Yagoo Bot is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Yagoo Bot.  If not, see <http://www.gnu.org/licenses/>.
"""

import discord
import asyncio
from typing import Union
from discord.ext import commands
from yagoo.lib.prompts import TwitterPrompts, removeMessage
from yagoo.scrapers.infoscraper import FandomScrape, TwitterScrape
from yagoo.lib.botUtils import TwitterUtils, embedContinue, getRoles, msgDelete, fandomTextParse, vtuberSearch
from yagoo.lib.dataUtils import botdb, dbTools
from yagoo.types.error import NoFollows
from yagoo.types.message import YagooMessage

async def botHelp(prefix: str):
    hembed = discord.Embed(title="Yagoo Bot Commands")
    hembed.description = "Currently the bot only has a small number of commands, as it is still in development!\n" \
                         "New stream notifications will be posted on a 3 minute interval, thus any new notifications " \
                         "will not come immediately after subscribing.\n" \
                         f"Currently all the commands (except for `{prefix}help` and `{prefix}info`) require the user to have either the `Administrator` or `Manage Webhook` permission in the channel or server.\n" \
                         "Anything in angle brackets `<>` are required, leaving them will result in an error. " \
                         "Meanwhile, anything in square brackets `[]` are optional, so leaving them will also make the command work."
    
    hembed.add_field(name="Commands",
                     value=f"**{prefix}sub** [VTuber Name] (Alias: subscribe)\n"
                           "Brings up a list of channels to subscribe to.\n"
                           "Add a non-Hololive VTuber's name to the command to opt in to their notifications.\n\n"
                           f"**{prefix}unsub** (Alias: unsubscribe)\n"
                           "Brings up a list of channels to unsubscribe to.\n\n"
                           f"**{prefix}sublist** (Alias: subs, subslist)\n"
                           "Brings up a list of channels that the current chat channel has subscribed to.\n\n"
                           f"**{prefix}subdefault** (Alias: subDefault)\n"
                           "Set's the default subscription type for the channel.\n\n"
                           f"**{prefix}follow** (Alias: subDefault)\n"
                           "Follows a custom Twitter account's tweets to the channel.\n\n"
                           f"**{prefix}follow** (Alias: subDefault)\n"
                           "Unfollows an already followed custom Twitter account from the channel.\n\n"
                           f"**{prefix}info** <VTuber Name> (Alias: getinfo)\n"
                           "Gets information about a VTuber.\n\n"
                           f"**{prefix}prefix** <VTuber Name>\n"
                           "Changes the prefix used by the bot.",
                     inline=False)
    
    hembed.add_field(name="Issues/Suggestions?",
                     value="If you run into any problems with/have any suggestions for the bot, then feel free to join the [support server](https://discord.gg/GJd6sdNjeQ) and drop a message there.",
                     inline=False)

    return hembed

# TODO: (LATER) Rewrite to use new prompts format
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

        if excessParts is None:
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

async def botAssignRoles(ctx: Union[commands.Context, SlashContext], bot: commands.Bot):
    db = await botdb.getDB()
    roles = await getRoles(ctx, True)
    subs = await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), ("livestream", "milestone", "premiere"), db)
    channels = await botdb.getAllData("channels", ("id", "name", "category"), keyDict="id", db=db)
    roleMsg = await ctx.send("Loading channel subscriptions...")
    affiliate = await rolePrompts.getAffiliations(subs, channels)
    print(affiliate)
    userChoice = await rolePrompts.promptAffiliate(ctx, bot, roleMsg, affiliate)
    print(userChoice)
    userChoice = await rolePrompts.promptChannel(ctx, bot, roleMsg, )

# Tasklist:
# TODO: Create disclaimer on core unsubscribe command
class botTwt:
    async def follow(cmd: Union[commands.Context, discord.Interaction], bot: commands.Bot, accLink: str):
        db = await botdb.getDB()
        if not accLink:
            raise ValueError("No Twitter ID")
        
        if isinstance(cmd, commands.Context):
            message = YagooMessage(bot, cmd.author)
            message.msg = await cmd.send("Searching for the Twitter user...")
        else:
            message = YagooMessage(bot, cmd.user)
        twtHandle = await TwitterUtils.getScreenName(accLink)
        twtUser = await TwitterScrape.getUserDetails(twtHandle)
        
        message.embed.title = f"Following {twtUser.name} to this channel"
        message.embed.description = "Do you want to follow this Twitter account?"
        message.addButton(1, "cancel", "Cancel", style=discord.ButtonStyle.red)
        message.addButton(1, "confirm", "Confirm", style=discord.ButtonStyle.green)
        
        if isinstance(cmd, commands.Context):
            result = await message.legacyPost(cmd)
        else:
            result = await message.post(cmd, True, True)
        
        if result.buttonID == "confirm":
            await dbTools.serverGrab(bot, str(cmd.guild.id), str(cmd.channel.id), ("url",), db)
            dbExist = await TwitterUtils.dbExists(twtUser.id_str, db)
            if not dbExist["status"]:
                await TwitterUtils.newAccount(twtUser, db)
            status = await TwitterUtils.followActions("add", str(cmd.channel.id), [twtUser.id_str], db=db)
            TwitterPrompts.follow.displayResult(message, twtUser.screen_name, status)
            message.msg = await message.msg.edit(content=None, embed=message.embed, view=None)
            await removeMessage(cmd=cmd)
            return
        await removeMessage(message, cmd)
    
    async def unfollow(cmd: Union[commands.Context, discord.Interaction], bot: commands.Bot):
        db = await botdb.getDB()
        if isinstance(cmd, commands.Context):
            message = YagooMessage(bot, cmd.author)
            message.msg = await cmd.send("Loading custom Twitter accounts...")
        else:
            message = YagooMessage(bot, cmd.user)

        server = await dbTools.serverGrab(bot, str(cmd.guild.id), str(cmd.channel.id), ("custom",), db)
        customTwt = await botdb.getAllData("twitter", ("twtID", "name", "screenName"), 1, "custom", "twtID", db)
        followedData = await botdb.listConvert(server["custom"])
        if followedData == [''] or followedData == [] or not followedData:
            raise NoFollows(cmd.channel.id)
        followData = await TwitterPrompts.unfollow.parse(followedData, customTwt)
        userPick = await TwitterPrompts.unfollow.prompt(cmd, message, followData)
        if userPick.status:
            await TwitterUtils.followActions("remove", str(cmd.channel.id), userPick.accountIDs(), userPick.allAccounts, db)
            TwitterPrompts.unfollow.displayResult(message, userPick)
            message.msg = await message.msg.edit(content=None, embed=message.embed, view=None)
            await removeMessage(cmd=cmd)
        else:
            await removeMessage(message, cmd)
