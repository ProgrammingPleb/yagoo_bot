# TODO: Split into seperate package

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

import asyncio
import traceback
import discord
import discord_slash
from typing import Union
from discord.ext import commands
from discord_slash.context import ComponentContext, SlashContext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import create_actionrow, create_button, create_select, create_select_option, wait_for_component
from yagoo.lib.botVars import allSubTypes
from yagoo.lib.dataUtils import botdb
from yagoo.types.data import CategorySubscriptionResponse, ChannelSearchResponse, SubscriptionData, SubscriptionResponse
from yagoo.types.message import YagooMessage
from yagoo.types.views import YagooSelectOption, YagooViewResponse

async def botError(ctx: commands.Context, error):
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
        for perm in iter(ctx.guild.permissions_for(ctx.author)):
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
    elif "50 - User not found." in str(error):
        errEmbed.description = "This user was not found on Twitter!\n" \
                               "Make sure the spelling of the user's Twitter link/screen name is correct!"
    elif "No Follows" in str(error):
        errEmbed.description = "This channel is not following any Twitter accounts.\n" \
                               "Follow a Twitter account's tweets by using `y!follow` or `/follow` command."
    elif isinstance(error, commands.CheckFailure):
        errEmbed.description = "You are missing permissions to use this bot.\n" \
                               "Ensure that you have one of these permissions for the channel/server:\n\n" \
                               " - `Administrator (Server)`\n - `Manage Webhooks (Channel/Server)`"
    elif isinstance(error, discord.errors.Forbidden):
        errEmbed.description = "The bot is missing permissions for this server/channel!\n" \
                               "Ensure that you have set these permissions for the bot to work:\n\n" \
                               "- Manage Webhooks\n- Send Messages\n- Manage Messages"
    else:
        errEmbed.description = "An unknown error has occurred.\nPlease report this to the support server!"
        print("An unknown error has occurred.")
        traceback.print_exception(type(error), error, error.__traceback__)
        print(error)
    errEmbed.add_field(name="Found a bug?", value="Report the bug to the [support server](https://discord.gg/GJd6sdNjeQ) to ensure"
                                                  " that the bug is fixed.")
    
    return errEmbed

# DEPRECATE: Use buttons to match new prompts format
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

# DEPRECATE: Use buttons to match new prompts format
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

class generalPrompts:
    class utils:
        async def buttonCheck(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message):
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
            def check(res: discord_slash.ComponentContext):
                return res.channel.id == ctx.channel.id and res.author.id == ctx.author.id and res.origin_message.id == msg.id
            
            try:
                data = await wait_for_component(bot, msg, check=check, timeout=30.0)
            except asyncio.TimeoutError:
                return False
            return data

        async def doubleCheck(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, filterRes: list = None):
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
                if filterRes:
                    return m.content in filterRes and m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
                return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id
            
            def bCheck(res: discord_slash.ComponentContext):
                return res.channel.id == ctx.channel.id and res.author.id == ctx.author.id and res.origin_message.id == msg.id

            done, pending = await asyncio.wait([wait_for_component(bot, msg, check=bCheck, timeout=30), bot.wait_for("message", check=mCheck, timeout=30)], return_when=asyncio.FIRST_COMPLETED)

            for future in done:
                future.exception()
            
            for future in pending:
                future.cancel()

            try:
                result = done.pop().result()
            except Exception as e:
                if isinstance(e, asyncio.TimeoutError):
                    return False
                await botError(ctx, "AsyncIO Wait Error")
            
            return result
        
        async def convertToRows(rows: list):
            """
            Converts a list of button rows to be used for the prompts.
            
            Arguments
            ---
            rows: A list of the button rows.
            
            Returns
            ---
            A `list` containing a list of buttons converted with `create_actionrow`.
            """
            rows = [create_actionrow(*row) for row in rows]
            return rows

        async def convertToSelect(options: list, minItems: int, maxItems: int):
            """
            Converts a list of options to be used for the prompts.
            
            Arguments
            ---
            options: A list of the options.
            
            Returns
            ---
            A `list` containing a list of pages with options converted with `create_select`.
            """
            result = []
            temp = []
            for option in options:
                if len(temp) == 25:
                    result.append(create_select([create_select_option(label=item["name"], value=item["id"]) for item in temp], "picker", min_values=minItems, max_values=maxItems))
                    temp = []
                temp.append(option)
            if len(temp) > 0:
                if maxItems > len(temp):
                    maxItems = len(temp)
                result.append(create_select([create_select_option(label=item["name"], value=item["id"]) for item in temp], "picker", min_values=minItems, max_values=maxItems))
            return result
    
    async def cancel(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, title: str, description: str, allowed: list = None):
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
        await msg.edit(content=" ", embed=embed, components=[create_actionrow(create_button(label="Cancel", style=ButtonStyle.blue, custom_id="cancel"))])
        
        result = await generalPrompts.utils.doubleCheck(ctx, bot, msg)
        
        if isinstance(result, discord.Message):
            await result.delete()
            return {
                "status": True,
                "res": result.content
            }
        return {
            "status": False
        }
        
    async def confirm(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, title: str, action: str):
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
        yesno = [create_actionrow(create_button(style=ButtonStyle.red, label="No"), create_button(style=ButtonStyle.green, label="Yes"))]
        await msg.edit(content=" ", embed=embed, components=yesno)

        def check(res: ComponentContext):
            return res.channel.id == ctx.channel.id and res.author.id == ctx.author.id and res.origin_message.id == msg.id

        try:
            result = await wait_for_component(bot, msg, yesno, check, 30)
        except asyncio.TimeoutError:
            return {
                "status": False,
                "choice": None
            }
        else:
            if result.component["label"] == "No":
                return {
                    "status": True,
                    "choice": False
                }
            if result.component["label"] == "Yes":
                return {
                    "status": True,
                    "choice": True
                }
    
    async def search(query: str):
        """
        Prompts the user to pick a search result based on their query.
        
        Arguments
        ---
        
        Returns
        ---
        """
        embed = discord.Embed(title="Searching For A Channel", description=f"Search results for {query}")
        return

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
            pageButtons.append([create_button(label=f"Page {pageNum + 1}/{len(pages)}", disabled=True, style=ButtonStyle.grey)])
            if pageNum == 0:
                pageButtons[0].insert(0, create_button(custom_id="back", emoji="⬅️", disabled=True, style=ButtonStyle.grey))
                pageButtons[0].append(create_button(custom_id="next", emoji="➡️", style=ButtonStyle.blue))
            elif pageNum == (len(pages) - 1):
                pageButtons[0].insert(0, create_button(custom_id="back", emoji="⬅️", style=ButtonStyle.blue))
                pageButtons[0].append(create_button(custom_id="next", emoji="➡️", disabled=True, style=ButtonStyle.grey))
            else:
                pageButtons[0].insert(0, create_button(custom_id="back", emoji="⬅️", style=ButtonStyle.blue))
                pageButtons[0].append(create_button(custom_id="next", emoji="➡️", style=ButtonStyle.blue))
            
            return pageButtons
        
        async def doubleCheck(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, pages: list, pageNum: int):
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
            
            def bCheck(res: ComponentContext):
                return res.channel.id == ctx.channel.id and res.author.id == ctx.author.id and res.origin_message.id == msg.id

            done, pending = await asyncio.wait([wait_for_component(bot, msg, check=bCheck, timeout=30), bot.wait_for("message", check=mCheck, timeout=30)], return_when=asyncio.FIRST_COMPLETED)

            for future in done:
                future.exception()
            
            for future in pending:
                future.cancel()

            try:
                result = done.pop().result()
            except Exception as e:
                if isinstance(e, asyncio.TimeoutError):
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
            return int(msg.content)
        
        async def processButton(data: discord_slash.ComponentContext, buttons: list, numReturn: list):
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
                if data.component["custom_id"] == x:
                    return numReturn[i]
                i += 1
            raise ValueError("The button ID does not match any key in the buttons ID list!")

    class remove:
        """
        A template for a message with an additional "remove all" button.
        """
        async def editMsg(bot: commands.Bot,
                          msg: discord.Message,
                          pages: list,
                          removeText: str,
                          embed: discord.Embed,
                          pageNum: int,
                          picker: bool = False,
                          minItems: int = 1,
                          maxItems: int = 1):
            """
            Edits the prompt with it's corresponding buttons.
            Should not be used outside of the `pageNav.minimal` class.
            """
            pageButtons = []
            if picker:
                pageButtons.append([pages[pageNum]])
            if len(pages) > 1:
                pageButtons.append((await pageNav.utils.pageRow(pages, pageNum))[0])
            pageButtons.append([create_button(custom_id="remove", label=removeText, style=ButtonStyle.red), create_button(custom_id="cancel", label="Cancel", style=ButtonStyle.blue)])
            await msg.edit(content=" ", embed=embed, components=await generalPrompts.utils.convertToRows(pageButtons))
        
        async def prompt(ctx: Union[commands.Context, SlashContext],
                         bot: commands.Bot,
                         msg: discord.Message,
                         pages: list,
                         title: str,
                         removeText: str,
                         description: str = None,
                         usePicker: bool = False,
                         minItems: int = 0,
                         maxItems: int = 0):
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
            buttonArgs = [["back", "next", "cancel", "remove"], [-1, 1, 2, 3]]
            if not usePicker:
                editArgs = [bot, msg, pages, removeText]
                result = await pageNav.message(ctx, bot, pageNav.remove, msg, pages, title, editArgs, buttonArgs, description)
            else:
                options = await generalPrompts.utils.convertToSelect(pages, minItems, maxItems)
                editArgs = [bot, msg, options, removeText]
                result = await pageNav.picker(ctx, bot, pageNav.remove, pages, msg, title, editArgs, buttonArgs, description, minItems, maxItems)
            if result["type"] == "button":
                if result["res"] == 2:
                    return {
                        "status": False,
                        "all": False,
                        "item": None
                    }
                return {
                    "status": True,
                    "all": True,
                    "item": None
                }
            if result["type"] == "select":
                return {
                    "status": True,
                    "all": False,
                    "item": {
                        "name": [item["name"] for item in result["selected"]],
                        "id": [item["id"] for item in result["selected"]]
                    }
                }
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
                          pageNum: int,
                          picker: bool = False,
                          minValue: int = 0,
                          maxValue: int = 0):
            """
            Edits the prompt with it's corresponding buttons.
            Should not be used outside of the `pageNav.minimal` class.
            """
            pageButtons = []
            if picker:
                pageButtons.append([pages[pageNum]])
            if len(pages) > 1:
                pageButtons.append((await pageNav.utils.pageRow(pages, pageNum))[0])
            pageButtons.append([create_button(custom_id="search", label=searchText, style=ButtonStyle.blue), create_button(custom_id=otherId, label=otherText, style=otherColor)])
            pageButtons.append([create_button(custom_id="cancel", label="Cancel", style=ButtonStyle.red)])
            await msg.edit(content=" ", embed=embed, components=await generalPrompts.utils.convertToRows(pageButtons))
        
        async def prompt(ctx: Union[commands.Context, SlashContext],
                         bot: commands.Bot,
                         msg: discord.Message,
                         pages: list,
                         title: str,
                         searchText: str,
                         otherText: str,
                         otherId: str,
                         otherColor: ButtonStyle = ButtonStyle.blue,
                         description: str = None,
                         usePicker: bool = False,
                         minItems: int = 1,
                         maxItems: int = 1):
            """
            Creates a prompt with the "search" template.
            
            Arguments
            ---
            ctx: Context from the command that is executed.
            bot: The Discord bot.
            msg: The Discord message that will be edited for the prompt.
            pages: A `list` containing all the pages for the prompt (or all the options if the picker is used).
            title: The title of the prompt.
            searchText: The contents of the "search" button.
            otherText: The contents of the other button.
            otherId: The ID for the other button.
            otherColor: The color of the other button. (Default is blue)
            description: An optional description to put behind the numbered list.
            usePicker: A `bool` indicating if a picker is needed.
            minItems: The minimum number of items that can be picked.
            maxItems: The maximum number of items that can be picked.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if the command succeeded.
            - other: `True` if the user clicked the other button.
            - search: `True` if the user wants to search for something.
            - item: The item that needs to added/removed. (Contains the "name" and "id" as `dict` keys)
            """
            buttonArgs = [["back", "next", "cancel", otherId, "search"], [-1, 1, 2, 3, 4]]
            if not usePicker:
                editArgs = [bot, msg, pages, searchText, otherText, otherId, otherColor]
                result = await pageNav.message(ctx, bot, pageNav.search, msg, pages, title, editArgs, buttonArgs, description)
            else:
                select = await generalPrompts.utils.convertToSelect(pages, minItems, maxItems)
                editArgs = [bot, msg, select, searchText, otherText, otherId, otherColor]
                result = await pageNav.picker(ctx, bot, pageNav.search, pages, msg, title, editArgs, buttonArgs, description, minItems, maxItems)
            
            if result["type"] == "button":
                if result["res"] == 2:
                    return {
                        "status": False,
                        "other": False,
                        "search": False,
                        "item": None
                    }
                if result["res"] == 3:
                    return {
                        "status": True,
                        "other": True,
                        "search": False,
                        "item": None
                    }
                if result["res"] == 4:
                    return {
                        "status": True,
                        "other": False,
                        "search": True,
                        "item": None
                    }
            elif result["type"] == "select":
                return {
                    "status": True,
                    "other": False,
                    "search": False,
                    "item": {
                        "name": [item["name"] for item in result["selected"]],
                        "id": [item["id"] for item in result["selected"]]
                    }
                }
            else:
                return {
                    "status": False
                }

    async def message(ctx: Union[commands.Context, SlashContext],
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
            
            if isinstance(result, discord_slash.ComponentContext):
                await result.defer(edit_origin=True)
                buttonRes = await pageNav.utils.processButton(result, *buttonArgs)
                if buttonRes in [-1, 1]:
                    pageNum += buttonRes
                else:
                    return {
                        "type": "button",
                        "res": buttonRes
                    }
            elif isinstance(result, discord_slash.ComponentMessage):
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
    
    async def picker(ctx: Union[commands.Context, SlashContext],
                      bot: commands.Bot,
                      editClass: type,
                      pages: list,
                      msg: discord.Message,
                      title: str,
                      editArgs: list,
                      buttonArgs: list,
                      description: str,
                      minItems: int,
                      maxItems: int):
        """
        Create a picker prompt with the specified message edit class and it's arguments, and button responses.
        
        Arguments
        ---
        ctx: Context from the command that is executed.
        bot: The Discord bot.
        editClass: The class that `editMsg` is a part of.
        msg: The Discord message that will be edited for the prompt.
        pages: A `list` containing all the available options.
        title: The title of the embed.
        editArgs: A `list` containing the arguments for `editMsg`.
        buttonArgs: A `list` containing the arguments for the button check function.
        minItems: The minimum number of items that can be picked.
        maxItems: The maximum number of items that can be picked.
        
        Options Format
        ---
        Each options object must have a `dict` containing:
        - name: The label for the option.
        - id: The identifier for the option.
        
        Returns
        ---
        A `dict` with:
        - type: Possible outputs are `button`, `message`, or `None`.
        - res: The response of the interaction type.
        """
        pageNum = 0
        embed = discord.Embed(title=title)
        if maxItems > 1:
            embedtext = "Pick the entries in the list or use the buttons below for other actions."
        else:
            embedtext = "Pick an entry in the list or use the buttons below for other actions."
        embed.add_field(name="Actions", value=embedtext)

        while True:
            if description:
                embed.description = description
            await editClass.editMsg(*editArgs, embed, pageNum, True, minItems, maxItems)
            result = await generalPrompts.utils.buttonCheck(ctx, bot, msg)
            
            if isinstance(result, discord_slash.ComponentContext):
                await result.defer(edit_origin=True)
                if result.component_type == 2:
                    buttonRes = await pageNav.utils.processButton(result, *buttonArgs)
                    if buttonRes in [-1, 1]:
                        pageNum += buttonRes
                    else:
                        return {
                            "type": "button",
                            "res": buttonRes
                        }
                elif result.component_type == 3:
                    picks = []
                    for item in pages:
                        if item["id"] in result.selected_options:
                            picks.append(item)
                    return {
                        "type": "select",
                        "res": result,
                        "selected": picks
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
        
        Returns
        ---
        A `list` of containing `dict` objects with the affiliations following the options specifications.
        """
        exists = []
        result = []
        for channel in data:
            if data[channel]["category"] not in exists:
                result.append({"name": data[channel]["category"], "id": data[channel]["category"]})
                exists.append(data[channel]["category"])
        
        return result
    
    async def ctgPicker(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, channels: dict, ctgMsg: discord.Message):
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
        result = await pageNav.search.prompt(ctx, bot, ctgMsg, pages, "Subscribing to a VTuber", "Search for a VTuber", "Subscribe to all VTubers", "subAll", description=description, usePicker=True, minItems=1, maxItems=1)
        
        if result["status"]:
            if not result["other"] and not result["search"]:
                return {
                    "status": True,
                    "all": result["other"],
                    "search": result["search"],
                    "category": result["item"]["name"][0]
                }
            return {
                "status": True,
                "all": result["other"],
                "search": result["search"],
                "category": None
            }
        return {
            "status": False
        }
    
    async def searchPick(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, searchTerm: str, results: list):
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
                subTypes += f"{subType.capitalize()}, "
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
                embed.add_field(name="Subscription Types", value=subTypes.strip(", "), inline=False)
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
            A `list` following the options specifications in `pageNav.picker`.
            """
            result = []
            
            for channel in category:
                if 25 < len(category[channel]["name"]) > 22:
                    name = (category[channel]["name"])[:22] + "..."
                else:
                    name = category[channel]["name"]
                result.append({"name": name, "id": channel})
            
            return result
        
        async def prompt(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, category: dict, catName: str):
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
            return await pageNav.search.prompt(ctx, bot, msg, pages, "Subscribing to a VTuber", "Search for a VTuber", f"Subscribe to all {catName} VTubers", "subAll", usePicker=True, maxItems=25)
    
    class subTypes:
        async def editMsg(subTypes: list, msg: discord.Message, embed: discord.Embed, buttonStates: dict, subText: str, subId: str, allowNone: bool):
            buttonList = []
            selected = False
            allTypes = True
            for subType in subTypes:
                if buttonStates[subType]:
                    buttonList.append([create_button(label=f"{subType.capitalize()} Notifications", style=ButtonStyle.green, custom_id=subType)])
                    selected = True
                else:
                    buttonList.append([create_button(label=f"{subType.capitalize()} Notifications", style=ButtonStyle.red, custom_id=subType)])
                    allTypes = False
            if allowNone:
                selected = True
            if not allTypes:
                allButton = create_button(label="Select All", style=ButtonStyle.blue, custom_id="all")
            else:
                allButton = create_button(label="Select None", custom_id="all", style=ButtonStyle.grey)
            buttonList.append([create_button(label=f"Cancel", style=ButtonStyle.red, custom_id="cancel"), allButton, create_button(label=subText, style=ButtonStyle.green, custom_id=subId, disabled=not selected)])
            await msg.edit(content=" ", embed=embed, components=await generalPrompts.utils.convertToRows(buttonList))
            return
        
        async def prompt(ctx: Union[commands.Context, SlashContext],
                         bot: commands.Bot,
                         msg: discord.Message,
                         title: str,
                         description: str,
                         buttonText: str = "Subscribe",
                         buttonId: str = "subscribe",
                         subTypes: dict = None,
                         allowNone: bool = False):
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
            subTypes: Existing subscription type status as a `dict`.
            allowNone: To allow the user to select none of the subscription types.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if the user choosed any subscription types.
            - subTypes: The subscription types which were selected by the user (`dict` that contains `bool` states of subscriptions).
            """
            buttonStates = subTypes
            if not buttonStates:
                buttonStates = {}
                subTypes = allSubTypes(False)
                for subType in subTypes:
                    buttonStates[subType] = False
            
            embed = discord.Embed(title=title, description=description)
            
            while True:
                await subPrompts.subTypes.editMsg(subTypes, msg, embed, buttonStates, buttonText, buttonId, allowNone)
                result = await generalPrompts.utils.buttonCheck(ctx, bot, msg)
                
                if result:
                    await result.defer(edit_origin=True)
                    if result.component["custom_id"] not in ["cancel", "all", buttonId]:
                        buttonStates[result.component["custom_id"]] = not buttonStates[result.component["custom_id"]]
                    elif result.component["custom_id"] == "all":
                        allBool = True
                        for button in buttonStates:
                            if allBool:
                                allBool = buttonStates[button]
                        for button in buttonStates:
                            buttonStates[button] = not allBool
                    elif result.component["custom_id"] == "cancel":
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
            buttons = [[create_button(label="Cancel", style=ButtonStyle.red, custom_id="cancel"),
                        create_button(label="Search Results", style=ButtonStyle.blue, custom_id="results"),
                        create_button(label="Confirm", style=ButtonStyle.green, custom_id="confirm")]]
            await msg.edit(content=" ", embed=embed, components=await generalPrompts.utils.convertToRows(buttons))
            return
        
        async def prompt(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, title: str, action: str):
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
            embed = discord.Embed(title=title, description=f"Are you sure you want to {action} to this channel?")
            await subPrompts.vtuberConfirm.editMsg(msg, embed)
            result = await generalPrompts.utils.buttonCheck(ctx, bot, msg)
            
            if result:
                await result.defer(edit_origin=True)
                if result.component["custom_id"] == "cancel":
                    return {
                        "status": False
                    }
                if result.component["custom_id"] == "results":
                    return {
                        "status": True,
                        "action": "search"
                    }
                if result.component["custom_id"] == "confirm":
                    return {
                        "status": True,
                        "action": "confirm"
                    }
            else:
                return {
                    "status": False
                }
            return

    class sublistDisplay:
        async def parseToPages(server: dict):
            """
            Parses the channel's subscriptions into pages that can be used by `pageNav.message`.
            
            Arguments
            ---
            server: The server's channel subscriptions, obtained from `unsubUtils.parseToSubTypes`.
            
            Returns
            ---
            A `list` following the page format in `pageNav.message`.
            """
            result = []
            pos = 1
            text = ""
            for channel in server["channels"]:
                text += f"{pos}. {server['channels'][channel]['name']}\n"
                pos += 1
                if pos == 11:
                    result.append({"text": text.strip(), "entries": [], "ids": [], "names": []})
                    pos = 1
                    text = ""
            if pos > 1:
                result.append({"text": text.strip(), "entries": [], "ids": [], "names": []})
            return result
        
        async def editMsg(msg: discord.Message, embed: discord.Embed, pages: list, pagePos: int):
            buttons = []
            if len(pages) > 1:
                buttons = await pageNav.utils.pageRow(pages, pagePos)
            await msg.edit(content=" ", embed=embed, components=await generalPrompts.utils.convertToRows(buttons))
            return
        
        async def prompt(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, pages: list, server: dict):
            """
            Show the user about the current subscriptions for the channel.
            
            Arguments
            ---
            ctx: Context from the executed command.
            bot: The Discord bot.
            msg: The message that will be used as the prompt.
            pages: A `list` containing the pages of the Discord channel's subscriptions.
            server: The server's channel subscriptions, obtained from `unsubUtils.parseToSubTypes`.
            """
            embed = discord.Embed(title="Current Channel Subscriptions")
            pagePos = 0
            subFilter = []          # TODO: (LATER) Subscription filter as a sub-update after core rewrite
            
            while True:
                embed.description = pages[pagePos]["text"]
                await subPrompts.sublistDisplay.editMsg(msg, embed, pages, pagePos)
                result = await generalPrompts.utils.buttonCheck(ctx, bot, msg)
                
                if result:
                    await result.defer(edit_origin=True)
                    if result.component["custom_id"] == "next":
                        pagePos += 1
                    elif result.component["custom_id"] == "back":
                        pagePos -= 1
                else:
                    break
            
            if len(server['subbed']) > 1:
                embed.description = f"This channel is currently subscribed to {len(server['subbed'])} channels."
            else:
                embed.description = f"This channel is currently subscribed to 1 channel."
            await msg.edit(content=" ", embed=embed, components=[])
            return

class unsubPrompts:
    class removePrompt:
        async def editMsg(msg: discord.Message, embed: discord.Embed, subTypes: dict):
            buttons = []
            allSubs = True
            selected = False
            for subType in subTypes:
                if subTypes[subType]:
                    buttons.append([create_button(label=f"{subType.capitalize()} Notifications", custom_id=subType, style=ButtonStyle.green)])
                    allSubs = False
                else:
                    buttons.append([create_button(label=f"{subType.capitalize()} Notifications", custom_id=subType, style=ButtonStyle.grey)])
                    selected = True
            if not allSubs:
                buttons.append([create_button(label="Cancel", custom_id="cancel", style=ButtonStyle.red),
                                create_button(label="Select All", custom_id="select", style=ButtonStyle.blue),
                                create_button(label="Unsubscribe", custom_id="unsub", style=ButtonStyle.red, disabled=not selected)])
            else:
                buttons.append([create_button(label="Cancel", custom_id="cancel", style=ButtonStyle.red),
                                create_button(label="Select None", custom_id="select", style=ButtonStyle.grey),
                                create_button(label="Unsubscribe", custom_id="unsub", style=ButtonStyle.red, disabled=not selected)])
            await msg.edit(content=" ", embed=embed, components=await generalPrompts.utils.convertToRows(buttons))
            return
        
        async def prompt(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, msg: discord.Message, ids: list, names: list, subStates: dict):
            """
            Prompts the user for which subscription type to unsubscribe from.
            
            Arguments
            ---
            ctx: Context from the executed command.
            bot: The Discord bot.
            msg: The message that will be used as the prompt.
            ids: IDs of the VTuber channels to be unsubscribed from.
            names: Names of the VTuber channels to be unsubscribed from.
            subStates: The current active subscriptions for all the subscribed VTuber channels.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if an option was chosen by the user.
            - unsubbed: A `list` with subscription types to unsubscribe from.
            """
            if len(ids) > 1:
                name = "Multiple Channels"
            else:
                name = names[0]
            embed = discord.Embed(title=f"Unsubscribing from {name}", description="Choose the subscription types to unsubscribe from.")
            
            subTypes = {}
            if ids[0] != "channelAllUnsub":
                for channel in ids:
                    for subType in subStates[channel]["subTypes"]:
                        if subType not in subTypes:
                            subTypes[subType] = True
            else:
                subTypes = subStates
            
            while True:
                await unsubPrompts.removePrompt.editMsg(msg, embed, subTypes)
                result = await generalPrompts.utils.buttonCheck(ctx, bot, msg)
                
                if result:
                    await result.defer(edit_origin=True)
                    if result.component["custom_id"] == "cancel":
                        return {
                            "status": False
                        }
                    if result.component["custom_id"] == "unsub":
                        unsubbed = []
                        for subType in subTypes:
                            if not subTypes[subType]:
                                unsubbed.append(subType)
                        return {
                            "status": True,
                            "unsubbed": unsubbed
                        }
                    if result.component["custom_id"] == "select":
                        allSubs = True
                        for subType in subTypes:
                            if subTypes[subType]:
                                allSubs = False
                        for subType in subTypes:
                            subTypes[subType] = allSubs
                    else:
                        subTypes[result.component["custom_id"]] = not subTypes[result.component["custom_id"]]
                else:
                    return {
                        "status": False
                    }

    async def displayResult(msg: discord.Message, name: str, subTypes: list):
        subTypeText = ""
        
        embed = discord.Embed(title="Successfully Unsubscribed!",
                              description=f"This channel is now unsubscribed from {name}.",
                              color=discord.Colour.green())
        for subType in subTypes:
            subTypeText += f"{subType.capitalize()}, "
        embed.add_field(name="Subscription Types", value=subTypeText.strip(", "), inline=False)
        await msg.edit(content=" ", embed=embed, components=[])
        return

class TwitterPrompts:
    class unfollow:
        async def parseToOptions(subbed: list, data: dict):
            """
            Parses a list of Twitter accounts into a list matching the pages specification in `pageNav.picker`.
            
            Arguments
            ---
            subbed: A `list` containing the Twitter accounts to be parsed.
            data: A `dict` containing the Twitter custom accounts data.
            
            Returns
            ---
            A list containing `dict` objects matching the specification in `pageNav.picker`.
            """
            options = []
            
            for twtID in subbed:
                if 22 < len(data[twtID]["name"]) > 25:
                    name = data[twtID]["name"][:22] + "..."
                else:
                    name = data[twtID]["name"]
                options.append({"name": name, "id": twtID})
            
            return options
        
        async def parseToPages(options: list):
            """
            Parses a list of options into select pages.
            
            Arguments
            ---
            options: A `list` of all the available options.
            
            Returns
            ---
            A `list` with with `list` objects up to 25 options.
            """
            pages = []
            temp = []
            
            for option in options:
                if len(temp) == 25:
                    pages.append(temp)
                    temp = []
                temp.append(option)
            if len(temp) != 0:
                pages.append(temp)
            
            return pages
        
        async def prompt(ctx: Union[SlashContext, commands.Context], bot: commands.Bot, msg: discord.Message, options: dict):
            """
            Prompts the user for which Twitter accounts to be unfollowed.
            
            Arguments
            ---
            ctx: Context from the executed command.
            bot: The Discord bot.
            msg: The message that will be used as the prompt.
            options: A `dict` containing the Twitter custom accounts data.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if an option was chosen by the user.
            - all: A `bool` indicating whether all the Twitter accounts should be unfollowed.
            - unfollowed: A `dict` with the Twitter accounts name and ids as keys to be unfollowed.
            """
            result = await pageNav.remove.prompt(ctx, bot, msg, options, "Unfollowing from Twitter Accounts", "Unfollow all accounts", "Choose the account to be unfollowed.", True, 1, 25)
            if not result["status"]:
                return {
                    "status": False,
                    "all": False,
                    "unfollowed": {}
                }
            if result["all"]:
                return {
                    "status": True,
                    "all": True,
                    "unfollowed": {}
                }
            return {
                "status": True,
                "all": False,
                "unfollowed": {"names": [item for item in result["item"]["name"]],
                                "ids": [item for item in result["item"]["id"]]},
            }
    
    async def displayResult(msg: discord.Message, action: str, success: bool, username: str = None, allAccount = False):
        """
        Display the result of the follow/unfollow action to the user.
        
        Arguments
        ---
        msg: The message that will be used as the prompt.
        action: The Twitter action that has been done.
        success: A `bool` that indicates if the action was successful or otherwise.
        username: The Twitter handle of the account.
        all: A `bool` that indicates if all Twitter accounts were unfollowed.
        """
        embed = discord.Embed()
        if success:
            embed.color = discord.Colour.green()
            if action == "add":
                embed.title = "Successfully Followed!"
                embed.description = f"This channel is now following @{username}'s tweets."
            elif action == "remove":
                embed.title = "Successfully Unfollowed!"
                if not allAccount:
                    embed.description = f"This channel has now been unfollowed from {username} tweets."
                else:
                    embed.description = "This channel has now been unfollowed from all Twitter accounts in the list."
        else:
            embed.color = discord.Colour.red()
            embed.title="An error has occurred!"
            if action == "add":
                embed.description = f"This channel has already been following @{username}'s tweets."
            elif action == "remove":
                embed.description = f"This channel has not been following @{username}'s tweets."
        await msg.edit(content=" ", embed=embed, components=[])
        return

class rolePrompts:
    async def affiliationSelect(affiliations: list):
        result = []
        
        for affiliation in affiliations:
            result.append({"name": affiliation, "id": affiliation})
        
        return result
    
    async def channelSelect(channels: dict):
        result = []
        
        for channel in channels:
            result.append({"name": channels[channel], "id": channel})
        
        return result
    
    async def getAffiliations(channelSubs: dict, channelData: dict):
        """
        Gets the affiliations of the channel's current subscriptions.
        
        Arguments
        ---
        channelSubs: A `dict` containing the channel's current subscriptions.
        channelData: A `dict` containing all YouTube channels data.
        
        Returns
        ---
        A `dict` with the affiliations as keys and the corresponding channel IDs as values.
        """
        allChannels = []
        remove = []
        result = {}
        
        for subType in channelSubs:
            subs = await botdb.listConvert(channelSubs[subType])
            if subs:
                for channel in await botdb.listConvert(channelSubs[subType]):
                    if channel not in allChannels:
                        allChannels.append(channel)
        
        for channel in channelData:
            if channelData[channel]["category"] not in result:
                result[channelData[channel]["category"]] = {}
        
        for channel in allChannels:
            result[channelData[channel]["category"]][channel] = channelData[channel]["name"]
        
        for affiliation in result:
            if result[affiliation] == {}:
                remove.append(affiliation)
        
        for dictKey in remove:
            del result[dictKey]
        
        return result
    
    async def promptAffiliate(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, channelSubs: dict):
        affiliations = []
        for subType in channelSubs:
            affiliations.append(subType)
        affChoice = await pageNav.search.prompt(ctx, bot, msg, await rolePrompts.affiliationSelect(affiliations),
                                                "Adding Role Pings", "Search for a channel", "Add a role ping to every VTuber",
                                                "other", description="Pick an affiliation of the channel's notifications be role pinged.",
                                                usePicker=True, maxItems=1)
        if affChoice["status"]:
            if affChoice["other"]:
                return {
                    "status": True,
                    "action": "all"
                }
            if affChoice["search"]:
                return {
                    "status": True,
                    "action": "search"
                }
            return {
                "status": True,
                "action": "pick",
                "pick": affChoice["item"]["name"][0]
            }
        return {
            "status": False
        }
    
    async def promptChannel(ctx: commands.Context, bot: commands.Bot, msg: discord.Message, channelSubs: dict):
        chChoice = await pageNav.search.prompt(ctx, bot, msg,
                                            await rolePrompts.channelSelect(channelSubs[affChoice["item"]["name"][0]]),
                                            "Adding Role Pings", "Search for a channel",
                                            f"Add a role to every {affChoice['item']['name'][0]} VTubers", "other",
                                            description="Pick the channel's notifications to be role pinged.", usePicker=True,
                                            maxItems=25)
        if chChoice["status"]:
            if chChoice["other"]:
                return
            if chChoice["search"]:
                return
            return {
                "status": True
            }
        return {
            "status": False
        }
