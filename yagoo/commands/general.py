import discord
import asyncio
from typing import Union
from discord.ext import commands
from discord_slash.context import SlashContext
from ..scrapers.infoscraper import FandomScrape, TwitterScrape
from ..lib.botUtils import TwitterUtils, embedContinue, getRoles, msgDelete, fandomTextParse, vtuberSearch
from ..lib.dataUtils import botdb, dbTools
from ..lib.prompts import TwitterPrompts, generalPrompts, rolePrompts

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
    async def follow(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, accLink: str):
        db = await botdb.getDB()
        if not accLink:
            raise ValueError("No Twitter ID")
        
        twtMsg = await ctx.send("Searching for the Twitter user...")
        twtHandle = await TwitterUtils.getScreenName(accLink)
        twtUser = await TwitterScrape.getUserDetails(twtHandle)
        
        result = await generalPrompts.confirm(ctx, bot, twtMsg,
                                              f"Following {twtUser.name} to this channel",
                                              "subscribe to this Twitter account")
        
        if result["status"] and result["choice"]:
            await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), ("url",), db)
            dbExist = await TwitterUtils.dbExists(twtUser.id_str, db)
            if not dbExist["status"]:
                await TwitterUtils.newAccount(twtUser, db)
            status = await TwitterUtils.followActions("add", str(ctx.channel.id), twtUser.id_str, db=db)
            await TwitterPrompts.displayResult(twtMsg, "add", status, twtUser.screen_name)
            await msgDelete(ctx)
            return
        await twtMsg.delete()
        await msgDelete(ctx)
    
    async def unfollow(ctx: commands.Context, bot: commands.Bot):
        db = await botdb.getDB()
        twtMsg: discord.Message = await ctx.send("Loading custom Twitter accounts.")

        server = await dbTools.serverGrab(bot, str(ctx.guild.id), str(ctx.channel.id), ("custom",), db)
        customTwt = await botdb.getAllData("twitter", ("twtID", "name", "screenName"), 1, "custom", "twtID", db)
        if await botdb.listConvert(server["custom"]) == [''] or await botdb.listConvert(server["custom"]) == []:
            raise ValueError("No Follows")
        options = await TwitterPrompts.unfollow.parseToOptions(await botdb.listConvert(server["custom"]), customTwt)
        userPick = await TwitterPrompts.unfollow.prompt(ctx, bot, twtMsg, options)
        if userPick["status"]:
            if userPick["all"]:
                status = await TwitterUtils.followActions("remove", str(ctx.channel.id), allAccounts=True, db=db)
                names = None
            else:
                status = await TwitterUtils.followActions("remove", str(ctx.channel.id), userPick["unfollowed"]["ids"], db=db)
                names = ""
                if len(userPick["unfollowed"]["names"]) <= 5:
                    for userID in userPick["unfollowed"]["ids"]:
                        names += f"@{customTwt[userID]['screenName']}, "
                    names = names[:-2]
                else:
                    names = f"{len(userPick['unfollowed']['names'])} Twitter accounts'"
            await TwitterPrompts.displayResult(twtMsg, "remove", status, names, userPick["all"])
            await msgDelete(ctx)
        else:
            await twtMsg.delete()
            await msgDelete(ctx)
