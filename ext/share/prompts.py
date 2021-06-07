import asyncio
import traceback
import discord
import discord_components
import tweepy
from discord.ext import commands
from discord_components.interaction import InteractionType
from discord_slash.context import SlashContext
from discord_components import Button, ButtonStyle
from typing import Union
from ext.share.botVars import allSubTypes

async def subCheck(ctx, bot, subMsg, mode, chName):
    from ext.share.botUtils import serverSubTypes
    subOptions = allSubTypes() + ["All"]
    subText = ""
    subChoice = []
    subNum = 1

    for sub in subOptions:
        subText += f"{subNum}. {sub} Notifications\n"
        subChoice.append(str(subNum))
        subNum += 1
    
    if mode == 1:
        action = "Subscribe"
    elif mode == 2:
        action = "Unsubscribe"
    else:
        return {
            "success": False
        }
    
    subEmbed = discord.Embed(title=chName, description=f"{action} to the channel's:\n\n"
                                                        f"{subText}X. Cancel\n\n[Bypass this by setting the channel's default subscription type using `y!subdefault`.\n"
                                                        "Select multiple subscriptions by seperating them using commas, for example `1,3`.]")

    await subMsg.edit(content=" ", embed=subEmbed)

    uInput = {
        "success": False
    }

    def check(m):
        return (m.content.lower() in subChoice + ['x'] or "," in m.content) and m.author == ctx.author

    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await subMsg.delete()
            break
        else:
            await msg.delete()
            if msg.content in subChoice or ("," in msg.content and "x" not in msg.content.lower()):
                if subChoice[-1] not in msg.content.split(","):
                    sSubType = await serverSubTypes(msg, subChoice + ['x'], subOptions)
                    uInput["subType"] = sSubType["subType"]
                else:
                    subTypes = []
                    for sub in subOptions:
                        if sub != subOptions[-1]:
                            subTypes.append(sub.lower())
                    uInput["subType"] = subTypes
                uInput["success"] = True
                break
            elif msg.content.lower() == 'x':
                break
    
    return uInput

async def unsubCheck(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, chData: dict, unsubMsg: discord.Message):
    """
    Prompts the user for the choice of which subscription type to unsubscribe from.

    Arguments
    ---
    `ctx`: A discord.py `commmands.Context` or discord-py-slash-command `SlashContext` object.
    `bot`: A discord.py `commands.Bot` object
    `chData`: A dict containing `"name"` for the embed title and `"subType"` for available subscription types.
    `unsubMsg`: A discord.py `discord.Message` object.

    Returns a `dict` with `"success"` for the success code and `"subType"` for the chosen subscription types to unsubscribe from.
    """

    notifCount = 1
    embedChoice = []
    unsubEmbed = discord.Embed(title=chData["name"], description="Unsubscribe from the channel's:\n")
    
    for subType in chData["subType"]:
        unsubEmbed.description += f"{notifCount}. {subType.capitalize()} Notifications\n"
        embedChoice.append(str(notifCount))
        notifCount += 1
    unsubEmbed.description += "\nX. Cancel\n[Select multiple subscriptions by seperating them using commas, for example `1,3`.]"

    await unsubMsg.edit(content=" ", embed=unsubEmbed)


    def check(m):
        return (m.content.lower() in embedChoice + ["x"] or "," in m.content) and m.author == ctx.author

    while True:
        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "subType": None
            }
        await msg.delete()
        if msg.content in embedChoice:
            return {
                "success": True,
                "subType": [chData["subType"][int(msg.content) - 1]]
            }
        elif "," in msg.content and "x" not in msg.content.lower():
            valid = True
            returnData = {
                    "success": False,
                    "subType": []
                }
            for subType in msg.content.split(","):
                if valid:
                    try:
                        returnData["subType"].append(chData["subType"][int(subType) - 1])
                    except Exception as e:
                        valid = False
                else:
                    break
            if valid:
                returnData["success"] = True
                return returnData
        elif "x" in msg.content.lower():
            return {
                "success": False,
                "subType": None
            }

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
    elif "Missing Arguments" in str(error):
        errEmbed.description = "A command argument was not given when required to."
    elif "No Subscriptions" in str(error):
        errEmbed.description = "There are no subscriptions for this channel.\n" \
                               "Subscribe to a channel's notifications by using `y!sub` or `/sub` command."
    elif "No Twitter ID" in str(error):
        errEmbed.description = "There was no Twitter account link given!\n" \
                               "Ensure that the account's Twitter link or screen name is supplied to the command."
    elif isinstance(error, commands.CheckFailure):
        errEmbed.description = "You are missing permissions to use this bot.\n" \
                               "Ensure that you have one of these permissions for the channel/server:\n\n" \
                               " - `Administrator (Server)`\n - `Manage Webhooks (Channel/Server)`"
    elif type(error) == tweepy.NotFound:
        errEmbed.description = "This user was not found on Twitter!\n" \
                               "Make sure the spelling of the user's Twitter link/screen name is correct!"
    else:
        print("An unknown error has occurred.")
        traceback.print_exception(type(error), error, error.__traceback__)
        print(error)
    
    return errEmbed

async def searchPrompt(ctx, bot, sResults: list, smsg, embedDesc):
    sEmbed = discord.Embed(title="VTuber Search", description=embedDesc)
    sDesc = ""
    checkNum = []
    picked = False
    pickName = None

    x = 1
    for entry in sResults:
        sDesc += f'{x}. {entry}\n'
        checkNum.append(str(x))
        x += 1
        
    sEmbed.add_field(name="Search Results", value=sDesc.strip(), inline=False)
    sEmbed.add_field(name="Other Actions", value="X. Cancel", inline=False)

    await smsg.edit(content=" ", embed=sEmbed)

    def check(m):
        return m.content.lower() in checkNum + ['x'] and m.author == ctx.author
    
    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await smsg.delete()
            break
        if msg.content in checkNum:
            await msg.delete()
            pickName = sResults[int(msg.content) - 1]
            picked = True
            break
        elif msg.content.lower() == 'x':
            await msg.delete()
            break
        else:
            await msg.delete()
    
    if not picked:
        return {
            "success": False
        }
    
    return {
        "success": True,
        "name": pickName
    }

async def searchConfirm(ctx, bot, sName: str, smsg, embedDesc, accept, decline, url: bool = False):
    sEmbed = discord.Embed(title="VTuber Search", description=embedDesc)
    if not url:
        sEmbed.add_field(name="Actions", value=f"Y. {accept}\nN. {decline}\nX. Cancel", inline=False)
        choices = ["y", "n", "x"]
    else:
        sEmbed.add_field(name="Actions", value=f"Y. {accept}\nX. Cancel", inline=False)
        choices = ["y", "x"]

    await smsg.edit(content=" ", embed=sEmbed)

    def check(m):
        return m.content.lower() in choices and m.author == ctx.author
    
    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "declined": False
            }
        if msg.content.lower() == "y":
            await msg.delete()
            return {
                "success": True,
                "declined": False
            }
        if msg.content.lower() == "n":
            await msg.delete()
            return {
                "success": False,
                "declined": True
            }
        if msg.content.lower() == "x":
            await msg.delete()
            return {
                "success": False,
                "declined": False
            }
        await msg.delete()

async def ctgPicker(ctx, bot, channels, ctgMsg):
    catStr = ""
    categories = []
    catNum = []
    x = 1
    for channel in channels:
        if channels[channel]["category"] not in categories:
            catStr += f'{x}. {channels[channel]["category"]}\n'
            categories.append(channels[channel]["category"])
            catNum.append(str(x))
            x += 1
        
    catEmbed = discord.Embed(title="Channel Search", description="Choose the affiliation corresponding to the VTuber:\n"
                                                                 "If the affiliation is not in this list,search the VTuber to add it to the bot's database.")
    catEmbed.add_field(name="Affiliation", value=catStr.strip())
    catEmbed.add_field(name="Other Actions", value="S. Search for a VTuber\nX. Cancel")

    await ctgMsg.edit(content=" ", embed=catEmbed)

    def check(m):
        return m.content.lower() in catNum + ["s", "x"] and m.author == ctx.author
    
    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "search": False
            }
        if msg.content in catNum:
            await msg.delete()
            return {
                "success": True,
                "search": False,
                "category": categories[int(msg.content) - 1]
            }
        if msg.content.lower() == "s":
            await msg.delete()
            return {
                "success": False,
                "search": True
            }
        if msg.content.lower() == "x":
            await msg.delete()
            return {
                "success": False,
                "search": False
            }
        await msg.delete()

async def searchMessage(ctx, bot, srchMsg):
    searchEmbed = discord.Embed(title="VTuber Search")
    searchEmbed.description = "Enter a VTuber name:\n" \
                              "[Enter `cancel` to cancel searching.]"

    await srchMsg.edit(content=" ", embed=searchEmbed)

    def check(m):
        return m.author == ctx.author
    
    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "search": None
            }
        if msg.content.lower() == "cancel":
            await msg.delete()
            return {
                "success": False,
                "search": None
            }
        await msg.delete()
        return {
            "success": True,
            "search": msg.content
        }

class generalPrompts:
    async def confirm(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, title: str, action: str):
        from .botUtils import msgDelete

        embed = discord.Embed(title=title, description=f"Are you sure you want to {action}?")
        await msg.edit(content=" ", embed=embed, components=[[Button(label="No", style=ButtonStyle.red, id="no"), Button(label="Yes", style=ButtonStyle.blue, id="yes")]])

        def check(res):
            return res.channel.id == ctx.channel.id and res.user.id == ctx.author.id and res.message.id == msg.id

        try:
            result = await bot.wait_for("button_click", check=check, timeout=30)
        except asyncio.TimeoutError:
            await msg.delete()
            await msgDelete(ctx)
            return {
                "status": False,
                "choice": None
            }
        else:
            if result.component.id == "no":
                return {
                    "status": True,
                    "choice": False
                }
            elif result.component.id == "yes":
                return {
                    "status": True,
                    "choice": True
                }

class pageNav:
    class utils:
        async def doubleCheck(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, pages: list, pageNum: int):
            def mCheck(m):
                return m.content in pages[pageNum]["entries"] and m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
            
            def bCheck(res):
                return res.channel.id == ctx.channel.id and res.user.id == ctx.author.id and res.message.id == msg.id

            done, pending = await asyncio.wait([bot.wait_for("button_click", check=bCheck, timeout=30), bot.wait_for("message", check=mCheck, timeout=30)], return_when=asyncio.FIRST_COMPLETED)

            for future in done:
                future.exception()
            
            for future in pending:
                future.cancel()

            try:
                result = done.pop().result()
            except Exception as e:
                if type(e) == asyncio.TimeoutError:
                    return False
                await botError(ctx, "AsyncIO Wait Error")
            
            return result
        
        async def buttonCheck(bot: commands.Bot):

            return

    class minimal:
        async def editMsg(bot: commands.Bot, msg: discord.Message, embed: discord.Embed, pages: list, pageNum: int):
            pageButtons = []
            if len(pages) > 1:
                pageButtons.append([Button(label=f"Page {pageNum + 1}/{len(pages)}", disabled=True)])
                if pageNum == 0:
                    pageButtons[0].insert(0, Button(id="back", emoji="⬅️", disabled=True))
                    pageButtons[0].append(Button(id="next", emoji="➡️", style=ButtonStyle.blue))
                elif pageNum == (len(pages) - 1):
                    pageButtons[0].insert(0, Button(id="back", emoji="⬅️", style=ButtonStyle.blue))
                    pageButtons[0].append(Button(id="next", emoji="➡️", disabled=True))
                else:
                    pageButtons[0].insert(0, Button(id="back", emoji="⬅️", style=ButtonStyle.blue))
                    pageButtons[0].append(Button(id="next", emoji="➡️", style=ButtonStyle.blue))
            pageButtons.append([Button(id="unfollow", label="Unfollow All Users", style=ButtonStyle.red), Button(id="cancel", label="Cancel", style=ButtonStyle.blue)])
            await msg.edit(content=" ", embed=embed, components=pageButtons)

        
        async def processButton(data: discord_components.Interaction):
            if data.component.id == "back":
                return -1
            elif data.component.id == "next":
                return 1
            elif data.component.id == "cancel":
                return 2
            elif data.component.id == "unfollow":
                return 3
        
        async def processMsg(msg: discord.Message, pageData: dict):
            return {
                "status": True,
                "all": False,
                "channel": {
                    "name": pageData["names"][int(msg.content) - 1],
                    "id": pageData["ids"][int(msg.content) - 1]
                }
            }

        async def prompt(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, pages: list, title: str):
            pageNum = 0
            embed = discord.Embed(title=title)
            embed.add_field(name="Actions", value="Pick a number correlating to the entry in the list or use the buttons below for other actions.")

            while True:
                embed.description = pages[pageNum]["text"].strip()
                await pageNav.minimal.editMsg(bot, msg, embed, pages, pageNum)
                result = await pageNav.utils.doubleCheck(ctx, bot, msg, pages, pageNum)
                
                if type(result) == discord_components.Interaction:
                    await result.respond(type=InteractionType.DeferredUpdateMessage)
                    buttonRes = await pageNav.minimal.processButton(result)
                    if buttonRes == 2:
                        return {
                            "status": False,
                            "all": False,
                            "channel": None
                        }
                    elif buttonRes == 3:
                        return {
                            "status": True,
                            "all": True,
                            "channel": None
                        }
                    else:
                        pageNum += buttonRes
                elif type(result) == discord.Message:
                    if result.content in pages[pageNum]["entries"]:
                        await result.delete()
                        return await pageNav.minimal.processMsg(result, pages[pageNum])
                else:
                    return {
                        "status": False
                    }

class TwitterPrompts:
    async def parseToPages(data: list):
        pages = []

        for section in data:
            pos = 1
            temp = ""
            entries = []
            id_list = []
            names = []
            for account in section:
                temp += f"{pos}. {section[account]['name']} (@{section[account]['screen_name']})\n"
                entries.append(str(pos))
                id_list.append(account)
                names.append(section[account]['name'])
                pos += 1
            pages.append({"text": temp, "entries": entries, "ids": id_list, "names": names})
        
        return pages

    async def unfollow(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, customAcc: dict, servers: dict):
        from .botUtils import chunks, msgDelete, TwitterUtils
        temp = {}
        followed = []

        for account in servers[str(ctx.guild.id)][str(ctx.channel.id)]["custom"]:
            temp[account] = customAcc[account]
                
        for account in chunks(temp, SIZE=9):
            followed.append(account)
        
        pages = await TwitterPrompts.parseToPages(followed)
        prompt = await pageNav.minimal.prompt(ctx, bot, msg, pages, "Following an account")

        if not prompt["status"]:
            await msg.delete()
            await msgDelete(ctx)
        else:
            if not prompt["all"]:
                choiceText = f"unfollow from {prompt['channel']['name']}"
                choiceTitle = "Unfollowing from a Twitter account"
                resultText = f"@{prompt['channel']['name']}'s tweets are now unfollowed from this channel."
            else:
                choiceText = "unfollow from all Twitter accounts"
                choiceTitle = "Unfollowing from all Twitter accounts"
                resultText = f"All custom Twitter accounts are now unfollowed from this channel."
            
            choice = await generalPrompts.confirm(ctx, bot, msg, choiceTitle, choiceText)

            if choice["status"] and choice["choice"]:
                if not prompt["all"]:
                    await TwitterUtils.followActions("remove", str(ctx.guild.id), str(ctx.channel.id), prompt["channel"]["id"])
                else:
                    await TwitterUtils.followActions("remove", str(ctx.guild.id), str(ctx.channel.id), all=True)
                await msg.edit(content=resultText, embed=" ", components=[])
                await msgDelete(ctx)
            else:
                await msg.delete()
                await msgDelete(ctx)
                return
