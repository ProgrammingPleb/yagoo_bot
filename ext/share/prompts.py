import asyncio
import traceback
import discord
import discord_components
import tweepy
from typing import Union
from discord.ext import commands
from discord_components.interaction import InteractionType
from discord_slash.context import SlashContext
from discord_components import Button, ButtonStyle
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

# TODO: Use buttons to improve the prompt
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
    class utils:
        async def buttonCheck(ctx: commands.Context, bot: commands.Bot, msg: discord.Message):
            """
            Wait for a button press from the message provided.
            
            Arguments
            ---
            ctx: Context from the command executed.
            bot: The Discord bot.
            msg: The message that has the buttons.
            
            Returns
            ---
            The interaction data if a button was pressed within 30 seconds, `False` if otherwise.
            """
            def check(res):
                return res.channel.id == ctx.channel.id and res.user.id == ctx.author.id and res.message.id == msg.id
            
            try:
                data = await bot.wait_for("button_click", check=check, timeout=30)
            except asyncio.TimeoutError:
                return False
            return data

        async def doubleCheck(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, filter: list = None):
            """
            Checks for both a message or a button interaction from the user.
            
            Arguments
            ---
            ctx: Context from the executed command.
            bot: The Discord bot.
            msg: The Discord message that contains the buttons.
            filter: A list of allowed responses (if any).
            
            Returns
            ---
            A Discord message or interaction if either are passed within 30 seconds, or `False` if none.
            """
            def mCheck(m):
                if filter:
                    return m.content in filter and m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
                else:
                    return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
            
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
    
    async def cancel(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, title: str, description: str, allowed: list = None):
        """
        Creates a prompt with a "Cancel" button.
        
        Arguments
        ---
        ctx: Context from the executed command.
        bot: The Discord bot.
        msg: The Discord message that will be used for the prompt.
        title: The title of the prompt.
        description: The content of the prompt.
        allowed: A list of allowed responses.
        
        Returns
        ---
        A `dict` with:
        - status: `True` if there was a response from the user, `False` if the prompt was cancelled or no input was entered in 30 seconds.
        - res: The response from the user.
        """
        embed = discord.Embed(title=title, description=description)
        await msg.edit(content=" ", embed=embed, components=[Button(label="Cancel", style=ButtonStyle.blue, id="cancel")])
        
        result = await generalPrompts.utils.doubleCheck(ctx, bot, msg)
        
        if type(result) == discord_components.message.ComponentMessage:
            await result.delete()
            return {
                "status": True,
                "res": result.content
            }
        else:
            return {
                "status": False
            }
        
    async def confirm(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, title: str, action: str):
        """
        Creates a prompt for confirmation of an action.
        
        Arguments
        ---
        ctx: Context from the executed command.
        bot: The Discord bot.
        msg: Message to be used as the prompt.
        title: The title of the prompt.
        action: The action that is to be confirmed by the user.
        
        Returns
        ---
        A `dict` with:
        - status: `True` if an "Yes"/"No" was clicked within 30 seconds.
        - choice: `True` if "Yes" was clicked, `False` if "No" was clicked.
        """
        embed = discord.Embed(title=title, description=f"Are you sure you want to {action}?")
        await msg.edit(content=" ", embed=embed, components=[[Button(label="No", style=ButtonStyle.red, id="no"), Button(label="Yes", style=ButtonStyle.blue, id="yes")]])

        def check(res):
            return res.channel.id == ctx.channel.id and res.user.id == ctx.author.id and res.message.id == msg.id

        try:
            result = await bot.wait_for("button_click", check=check, timeout=30)
        except asyncio.TimeoutError:
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
        async def pageRow(pages: list, pageNum: int):
            """
            Generates a button row for page-based navigation.
            
            Arguments
            ---
            pages: A `list` containing all pages for the prompt.
            pageNum: The current page position relative to `pages`.
            
            Returns
            ---
            A `list` with the page navigation buttons as the first row.
            """
            pageButtons = []
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
            
            return pageButtons
        
        async def doubleCheck(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, pages: list, pageNum: int):
            """
            Checks for both a message or a button interaction from the user.
            
            Arguments
            ---
            ctx: Context from the executed command.
            bot: The Discord bot.
            msg: The Discord message that contains the buttons.
            pages: A list with the pages of the Discord message.
            pageNum: The current page position.
            
            Returns
            ---
            A Discord message or interaction if either are passed within 30 seconds, or `False` if none.
            """
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
        
        async def processMsg(msg: discord.Message):
            """
            Processes a message to get the user's choice(s).
            
            Arguments
            ---
            msg: The Discord message containing the response.
            
            Returns
            ---
            An `int` or a `list` from the user's input.
            """
            if "," in msg.content:
                returnList = []
                for option in msg.content.split(","):
                    if option.strip() != "":
                        returnList.append(int(option))
                return returnList
            else:
                return int(msg.content)
        
        async def processButton(data: discord_components.Interaction, buttons: list, numReturn: list):
            """
            Processes the button inputs from the user.
            
            Arguments
            ---
            data: The Discord interaction correlating to the button press from the user.
            buttons: A `list` containing the button IDs of the message.
            numReturn: A `list` containing the responses of their respective button IDs.
            
            Returns
            ---
            Any object correlating to the linked response of the button ID.
            """
            i = 0
            for x in buttons:
                if data.component.id == x:
                    return numReturn[i]
                i += 1
            raise ValueError("The button ID does not match any key in the buttons ID list!")

    class remove:
        """
        A template for a message with an additional "remove all" button.
        """
        async def editMsg(bot: commands.Bot, msg: discord.Message, pages: list, removeText: str, embed: discord.Embed, pageNum: int):
            """
            Edits the prompt with it's corresponding buttons.
            Should not be used outside of the `pageNav.minimal` class.
            """
            pageButtons = []
            if len(pages) > 1:
                pageButtons = await pageNav.utils.pageRow(pages, pageNum)
            pageButtons.append([Button(id="remove", label=removeText, style=ButtonStyle.red), Button(id="cancel", label="Cancel", style=ButtonStyle.blue)])
            await msg.edit(content=" ", embed=embed, components=pageButtons)
        
        async def prompt(ctx: commands.Context,
                         bot: commands.Bot,
                         msg: discord.Message,
                         pages: list,
                         title: str,
                         removeText: str,
                         description: str = None):
            """
            Creates a prompt with the "remove" template.
            
            Arguments
            ---
            ctx: Context from the command that is executed.
            bot: The Discord bot.
            msg: The Discord message that will be edited for the prompt.
            pages: A `list` containing all the pages for the prompt.
            title: The title of the prompt.
            removeText: The contents of the "remove all" button.
            description: An optional description to put behind the numbered list.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if the command succeeded, `False` if otherwise.
            - all: `True` if the user wants to remove all items, `False` if otherwise.
            - item: The item that needs to removed. (Contains the "name" and "id" as `dict` keys)
            """
            editArgs = [bot, msg, pages, removeText]
            buttonArgs = [["back", "next", "cancel", "remove"], [-1, 1, 2, 3]]
            result = await pageNav.message(ctx, bot, pageNav.remove, msg, pages, title, editArgs, buttonArgs, description)
            if result["type"] == "button":
                if result["res"] == 2:
                    return {
                        "status": False,
                        "all": False,
                        "item": None
                    }
                else:
                    return {
                        "status": True,
                        "all": True,
                        "item": None
                    }
            elif result["type"] == "message":
                if type(result["res"]) == list:
                    result["res"] = result["res"][0]
                return {
                    "status": True,
                    "all": False,
                    "item": {
                        "name": pages[result["pageNum"]]["names"][result["res"] - 1],
                        "id": pages[result["pageNum"]]["ids"][result["res"] - 1]
                    }
                }
            else:
                return {
                    "status": False
                }
    
    class search:
        """
        A template for a message with an additional "remove all" button.
        """
        async def editMsg(bot: commands.Bot,
                          msg: discord.Message,
                          pages: list,
                          searchText: str,
                          otherText: str,
                          otherId: str,
                          otherColor: ButtonStyle,
                          embed: discord.Embed,
                          pageNum: int):
            """
            Edits the prompt with it's corresponding buttons.
            Should not be used outside of the `pageNav.minimal` class.
            """
            pageButtons = []
            if len(pages) > 1:
                pageButtons = await pageNav.utils.pageRow(pages, pageNum)
            pageButtons.append([Button(id="search", label=searchText, style=ButtonStyle.blue), Button(id=otherId, label=otherText, style=otherColor)])
            pageButtons.append([Button(id="cancel", label="Cancel", style=ButtonStyle.red)])
            await msg.edit(content=" ", embed=embed, components=pageButtons)
        
        async def prompt(ctx: commands.Context,
                         bot: commands.Bot,
                         msg: discord.Message,
                         pages: list,
                         title: str,
                         searchText: str,
                         otherText: str,
                         otherId: str,
                         otherColor: ButtonStyle = ButtonStyle.blue,
                         description: str = None):
            """
            Creates a prompt with the "search" template.
            
            Arguments
            ---
            ctx: Context from the command that is executed.
            bot: The Discord bot.
            msg: The Discord message that will be edited for the prompt.
            pages: A `list` containing all the pages for the prompt.
            title: The title of the prompt.
            searchText: The contents of the "search" button.
            otherText: The contents of the other button.
            otherId: The ID for the other button.
            otherColor: The color of the other button. (Default is blue)
            description: An optional description to put behind the numbered list.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if the command succeeded, `False` if otherwise.
            - all: `True` if the user wants to remove all items, `False` if otherwise.
            - search: `True` if the user wants to search for something, `False` if otherwise.
            - item: The item that needs to added/removed. (Contains the "name" and "id" as `dict` keys)
            """
            editArgs = [bot, msg, pages, searchText, otherText, otherId, otherColor]
            buttonArgs = [["back", "next", "cancel", otherId, "search"], [-1, 1, 2, 3, 4]]
            result = await pageNav.message(ctx, bot, pageNav.search, msg, pages, title, editArgs, buttonArgs, description)
            if result["type"] == "button":
                if result["res"] == 2:
                    return {
                        "status": False,
                        "other": False,
                        "search": False,
                        "item": None
                    }
                elif result["res"] == 3:
                    return {
                        "status": True,
                        "other": True,
                        "search": False,
                        "item": None
                    }
                elif result["res"] == 4:
                    return {
                        "status": True,
                        "other": False,
                        "search": True,
                        "item": None
                    }
            elif result["type"] == "message":
                if type(result["res"]) == list:
                    result["res"] = result["res"][0]
                return {
                    "status": True,
                    "other": False,
                    "search": False,
                    "item": {
                        "name": pages[result["pageNum"]]["names"][result["res"] - 1],
                        "id": pages[result["pageNum"]]["ids"][result["res"] - 1]
                    }
                }
            else:
                return {
                    "status": False
                }

    async def message(ctx: commands.Context,
                      bot: commands.Bot,
                      editClass: type,
                      msg: discord.Message,
                      pages: list,
                      title: str,
                      editArgs: list,
                      buttonArgs: list,
                      description: str = None):
        """
        Create a prompt with the specified message edit class and it's arguments, and button responses.
        
        Arguments
        ---
        ctx: Context from the command that is executed.
        bot: The Discord bot.
        editClass: The class that `editMsg` is a part of.
        msg: The Discord message that will be edited for the prompt.
        pages: A `list` containing all the pages.
        title: The title of the embed.
        editArgs: A `list` containing the arguments for `editMsg`.
        buttonArgs: A `list` containing the arguments for the button check function.
        description: An optional description to put behind the numbered list.
        
        Pages Format
        ---
        Each object in the `list` must have a `dict` containing:
        - text: The text for the page as a frontend. (Must be formatted with newlines)
        - entries: The number input for the entries that exist for the page.
        - ids: A list of identifiers for the entries.
        - names: A list of names for the entries.
        
        Returns
        ---
        A `dict` with:
        - type: Possible outputs are `button`, `message`, or `None`.
        - res: The response of the interaction type.
        - pageNum: The current page position relative to `pages`. (Only exists when type is `message`)
        """
        pageNum = 0
        embed = discord.Embed(title=title)
        embed.add_field(name="Actions", value="Pick a number correlating to the entry in the list or use the buttons below for other actions.")

        while True:
            if description:
                embed.description = f"{description}\n\n" + pages[pageNum]["text"].strip()
            else:
                embed.description = pages[pageNum]["text"].strip()
            await editClass.editMsg(*editArgs, embed, pageNum)
            result = await pageNav.utils.doubleCheck(ctx, bot, msg, pages, pageNum)
            
            if type(result) == discord_components.Interaction:
                await result.respond(type=InteractionType.DeferredUpdateMessage)
                buttonRes = await pageNav.utils.processButton(result, *buttonArgs)
                if buttonRes in [-1, 1]:
                    pageNum += buttonRes
                else:
                    return {
                        "type": "button",
                        "res": buttonRes
                    }
            elif type(result) == discord_components.message.ComponentMessage:
                if result.content in pages[pageNum]["entries"]:
                    await result.delete()
                    return {
                        "type": "message",
                        "res": await pageNav.utils.processMsg(result),
                        "pageNum": pageNum
                    }
            else:
                return {
                    "type": None,
                    "res": None
                }

class subPrompts:
    async def parseToPages(data: list, keyID: str = None):
        """
        Parse the channels into pages.
        
        Arguments
        ---
        data: Data from the `channels` table.
        keyID: The key that will be used as an identifier in other functions.
        """
        pages = []
        
        pos = 1
        temp = ""
        entries = []
        id_list = []
        names = []
        for account in data:
            temp += f"{pos}. {data[account]['name']}\n"
            entries.append(str(pos))
            if keyID is None:
                id_list.append(account)
            else:
                id_list.append(data[account][keyID])
            names.append(data[account]['name'])
            pos += 1
            if pos == 9:
                pages.append({"text": temp.strip(), "entries": entries, "ids": id_list, "names": names})
                pos = 1
                temp = ""
                entries = []
                id_list = []
                names = []
        if len(entries) > 1:
            pages.append({"text": temp.strip(), "entries": entries, "ids": id_list, "names": names})

        return pages
    
    async def categoryPages(data: dict):
        """
        Parse the channels data into pages for channel affiliations.
        
        Arguments
        ---
        data: Data grabbed from the `channels` table.
        """
        pages = []
        temp = ""
        entries = []
        categories = []
        pageIDs = []
        catCount = 1
        for channel in data:
            if data[channel]["category"] not in categories:
                category = data[channel]["category"]
                categories.append(category)
                pageIDs.append(category)
                temp += f"{catCount}. {category}\n"
                entries.append(str(catCount))
                categories.append(category)
                catCount += 1
            if catCount == 10:
                pages.append({"text": temp.strip(), "entries": entries, "ids": pageIDs, "names": pageIDs})
                temp = ""
                entries = []
                pageIDs = []
                catCount = 1
        if entries != []:
            pages.append({"text": temp.strip(), "entries": entries, "ids": pageIDs, "names": pageIDs})
        
        return pages
    
    async def ctgPicker(ctx: commands.Context, bot: commands.Bot, channels: dict, ctgMsg: discord.Message):
        """
        Prompts the user for a VTuber's affiliation.
        
        Arguments
        ---
        ctx: Context from the executed command.
        bot: The Discord bot.
        channels: Data from `channels` in `dict` form, with `id` as the main key.
        ctgMsg: Message to be used as the prompt message.
        
        Returns
        ---
        A `dict` with:
        - status: `True` if the user picked a category, `False` if otherwise.
        - all: `True` if the user picks to subscribe to all VTubers.
        - search: `True` if the user picks to search for a VTuber.
        - category: Contains the name of the category, `None` if there is no category picked.
        """
        pages = await subPrompts.categoryPages(channels)
        description = "Pick the VTuber's affiliation:"
        result = await pageNav.search.prompt(ctx, bot, ctgMsg, pages, "Subscribing to a VTuber", "Search for a VTuber", "Subscribe to all VTubers", "subAll", description=description)
        
        if result["status"]:
            print(f"prompts.py/ctgPicker: {result}")
            if not result["other"] and not result["search"]:
                return {
                    "status": True,
                    "all": result["other"],
                    "search": result["search"],
                    "category": result["item"]["name"]
                }
            else:
                return {
                    "status": True,
                    "all": result["other"],
                    "search": result["search"],
                    "category": None
                }
        else:
            return {
                "status": False
            }
    
    async def searchPick(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, searchTerm: str, results: list):
        """
        A prompt to pick possible search matches.
        
        Arguments
        ---
        ctx: Context from the exectued command.
        bot: The Discord bot.
        msg: The message that will be used as the prompt.
        searchTerm: The search term by the user.
        results: A `list` containing the search results.
        
        Returns
        ---
        A `dict` with:
        - status: `True` if the user picked a result.
        - name: Name of the search result.
        """
        resFilter = []
        pos = 1
        embedContent = f"Search results for '{searchTerm}':\n"
        for item in results:
            embedContent += f"{pos}. {item}\n"
            resFilter.append(pos)
            pos += 1
        
        result = await generalPrompts.cancel(ctx, bot, msg, "Searching for a VTuber", embedContent, allowed=resFilter)
        
        if not result["status"]:
            return {
                "status": False
            }
            
        return {
            "status": True,
            "name": results[int(result["res"]) - 1]
        }
    
    async def displaySubbed(msg: discord.Message, allSub: bool = False, category: str = None, subbed: list = None, chName: str = None):
        """
        Gives a status to the user about subbed accounts.
        
        Arguments
        ---
        msg: The message that will be used as the display.
        allSub: If the subscription involves all VTubers (in a category or the whole database).
        category: The name of the category.
        subbed: A list containing all the successfully subscribed subscription types. (Must be supplied if `allSub` is `False`)
        chName: The name of the channel. (Must be supplied if `allSub` is `False`)
        """
        embed = discord.Embed()
        if allSub:
            embed.title = "Successfully Subscribed!"
            if category:
                category += " "
            else:
                category = ""
            embed.description = f"This channel is now subscribed to all {category}VTubers."
            embed.color = discord.Colour.green()
            subTypes = ""
            for subType in subbed:
                subTypes += f"{subType}, "
            embed.add_field(name="Subscription Types", value=subTypes.strip(", "))
        else:
            if subbed == []:
                embed.title = "Already Subscribed!"
                embed.description = f"This channel is already subscribed to {chName}!"
                embed.color = discord.Colour.red()
            else:
                embed.title = "Successfully Subscribed!"
                embed.description = f"This channel is now subscribed to {chName}."
                embed.color = discord.Colour.green()
                subTypes = ""
                for subType in subbed:
                    subTypes += f"{subType.capitalize()}, "
                embed.add_field(name="Subscription Types", value=subTypes.strip(", "))
        await msg.edit(content=" ", embed=embed, components=[])
    
    class channelPick:
        async def parseToPages(category: dict):
            """
            Parses a category to pages for prompt consumption.
            
            Arguments
            ---
            category: The category as a `dict` containing `id` as the header, `name` as the sub-key.
            
            Returns
            ---
            A `list` following the format in `pageNav.message`.
            """
            result = []
            text = ""
            entries = []
            ids = []
            names = []
            pos = 1
            
            for channel in category:
                chData = category[channel]
                text += f"{pos}. {chData['name']}\n"
                ids.append(channel)
                names.append(chData['name'])
                entries.append(str(pos))
                pos += 1
                if pos == 10:
                    result.append({"text": text.strip(), "entries": entries, "ids": ids, "names": names})
                    text = ""
                    entries = []
                    ids = []
                    names = []
                    pos = 1
            if pos > 1:
                result.append({"text": text.strip(), "entries": entries, "ids": ids, "names": names})
            
            return result
        
        async def prompt(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, category: dict, catName: str):
            """
            Prompts the user for which VTuber to pick.
            
            Arguments
            ---
            ctx: Context from the executed command.
            bot: The Discord bot.
            msg: The message that will be used as the prompt.
            category: The category as a `dict` containing `id` as the header, `name` as the sub-key.
            catName: The name of the category.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if the command succeeded, `False` if otherwise.
            - other: `True` if the user wants to subscribe to all VTubers in the category, `False` if otherwise.
            - search: `True` if the user wants to search for something, `False` if otherwise.
            - item: The VTuber that needs to added/removed. (Contains the "name" and "id" as `dict` keys)
            """
            pages = await subPrompts.channelPick.parseToPages(category)
            return await pageNav.search.prompt(ctx, bot, msg, pages, "Subscribing to a VTuber", "Search for a VTuber", f"Subscribe to all {catName} VTubers", "subAll")
    
    class subTypes:
        async def editMsg(subTypes: list, msg: discord.Message, embed: discord.Embed, buttonStates: dict, subText: str, subId: str):
            buttonList = []
            selected = False
            all = True
            for subType in subTypes:
                if buttonStates[subType]:
                    buttonList.append([Button(label=f"{subType.capitalize()} Notifications", style=ButtonStyle.green, id=subType)])
                    selected = True
                else:
                    buttonList.append([Button(label=f"{subType.capitalize()} Notifications", style=ButtonStyle.red, id=subType)])
                    all = False
            if not all:
                allButton = Button(label="Select All", style=ButtonStyle.blue, id="all")
            else:
                allButton = Button(label="Select None", id="all")
            buttonList.append([Button(label=f"Cancel", style=ButtonStyle.red, id="cancel"), allButton, Button(label=subText, style=ButtonStyle.green, id=subId, disabled=not selected)])
            await msg.edit(content=" ", embed=embed, components=buttonList)
            return
        
        async def prompt(ctx: commands.Context,
                         bot: commands.Bot,
                         msg: discord.Message,
                         title: str,
                         description: str,
                         buttonText: str = "Subscribe",
                         buttonId: str = "subscribe"):
            """
            Prompts the user for subscription types.
            
            Arguments
            ---
            ctx: Context from the executed command.
            bot: The Discord bot.
            msg: The message that will be used as the prompt.
            title: The title of the prompt.
            description: The content of the prompt.
            buttonText: The text for the subscribe button.
            buttonId: The ID for the subscribe button.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if the user choosed any subscription types.
            - subTypes: The subscription types which were selected by the user (`dict` that contains `bool` states of subscriptions).
            """
            subTypes = allSubTypes(False)
            buttonStates = {}
            for subType in subTypes:
                buttonStates[subType] = False
            
            embed = discord.Embed(title=title, description=description)
            
            while True:
                await subPrompts.subTypes.editMsg(subTypes, msg, embed, buttonStates, buttonText, buttonId)
                result = await generalPrompts.utils.buttonCheck(ctx, bot, msg)
                
                if result:
                    await result.respond(type=InteractionType.DeferredUpdateMessage)
                    if result.component.id not in ["cancel", "all", buttonId]:
                        buttonStates[result.component.id] = not buttonStates[result.component.id]
                    elif result.component.id == "all":
                        allBool = True
                        for button in buttonStates:
                            if allBool:
                                allBool = buttonStates[button]
                        for button in buttonStates:
                            buttonStates[button] = not allBool
                    elif result.component.id == "cancel":
                        return {
                            "status": False
                        }
                    else:
                        return {
                            "status": True,
                            "subTypes": buttonStates
                        }
                else:
                    return {
                        "status": False
                    }
    
    class vtuberConfirm:
        async def editMsg(msg: discord.Message, embed: discord.Embed):
            buttons = [[Button(label="Cancel", style=ButtonStyle.red, id="cancel"),
                        Button(label="Search Results", style=ButtonStyle.blue, id="results"),
                        Button(label="Confirm", style=ButtonStyle.green, id="confirm")]]
            await msg.edit(content=" ", embed=embed, components=buttons)
            return
        
        async def prompt(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, title: str):
            """
            Prompts to either confirm the choice of VTuber, cancel, or search for another VTuber.
            
            Arguments
            ---
            ctx: Context from the executed command.
            bot: The Discord bot.
            msg: The message that will be used for the prompt.
            title: The title of the prompt.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if a user requested to search or confirms the choice.
            - action: The action that is requested by the user (`search`/`confirm`).
            """
            embed = discord.Embed(title=title, description="Are you sure you want to subscribe to this channel?")
            await subPrompts.vtuberConfirm.editMsg(msg, embed)
            result = await generalPrompts.utils.buttonCheck(ctx, bot, msg)
            
            if result:
                await result.respond(type=InteractionType.DeferredUpdateMessage)
                if result.component.id == "cancel":
                    return {
                        "status": False
                    }
                elif result.component.id == "results":
                    return {
                        "status": True,
                        "action": "search"
                    }
                elif result.component.id == "confirm":
                    return {
                        "status": True,
                        "action": "confirm"
                    }
            else:
                return {
                    "status": False
                }
            return

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
            pages.append({"text": temp.strip(), "entries": entries, "ids": id_list, "names": names})
        
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
        prompt = await pageNav.remove.prompt(ctx, bot, msg, pages, "Unfollowing an account", "Unfollow All Users")

        if not prompt["status"]:
            await msg.delete()
            await msgDelete(ctx)
        else:
            if not prompt["all"]:
                choiceText = f"unfollow from {prompt['item']['name']}"
                choiceTitle = "Unfollowing from a Twitter account"
                resultText = f"@{prompt['item']['name']}'s tweets are now unfollowed from this channel."
            else:
                choiceText = "unfollow from all Twitter accounts"
                choiceTitle = "Unfollowing from all Twitter accounts"
                resultText = f"All custom Twitter accounts are now unfollowed from this channel."
            
            choice = await generalPrompts.confirm(ctx, bot, msg, choiceTitle, choiceText)

            if choice["status"] and choice["choice"]:
                if not prompt["all"]:
                    await TwitterUtils.followActions("remove", str(ctx.guild.id), str(ctx.channel.id), prompt["item"]["id"])
                else:
                    await TwitterUtils.followActions("remove", str(ctx.guild.id), str(ctx.channel.id), all=True)
                await msg.edit(content=resultText, embed=" ", components=[])
                await msgDelete(ctx)
            else:
                await msg.delete()
                await msgDelete(ctx)
                return
