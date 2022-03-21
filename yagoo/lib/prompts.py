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
from typing import Optional, Union, List
from discord.ext import commands
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

def checkCancel(responseData: YagooViewResponse):
            """
    Checks if the user wants to cancel the command or check if the user gave any response.
            
            Arguments
            ---
    responseData: The response data from the invoked command.
            """
    if responseData.responseType:
        if responseData.buttonID == "cancel":
            return True
                return False
    return True

async def removeMessage(message: Optional[YagooMessage] = None, cmd: Union[commands.Context, discord.Interaction, None] = None):
            """
    Removes the message resulting from an invoked command or remove the command invocation.
    Will also remove the command message if a command's context is given.
            
            Arguments
            ---
    message: The message from the bot.
    cmd: The command's context.
            """
    if isinstance(cmd, commands.Context):
        if message:
            await message.msg.delete()
        await cmd.message.delete()
    else:
        if message:
            message.resetMessage()
            message.embed.title = "This command was cancelled or has timed out."
            message.embed.description = "Please dismiss the message using the `Dismiss message` text below."
            message.embed.color = discord.Color.red()
            await message.msg.edit(content=None, embed=message.embed, view=None)

class subPrompts:
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
                result.append(YagooSelectOption(data[channel]["category"], data[channel]["category"]))
                exists.append(data[channel]["category"])
        
        return result
    
    async def ctgPicker(cmd: Union[commands.Context, discord.Interaction], channels: dict, ctgMsg: YagooMessage):
        """
        Prompts the user for a VTuber's affiliation.
        
        Arguments
        ---
        ctx: Context or interaction from the executed command.
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
        categories = await subPrompts.categoryPages(channels)
        
        ctgMsg.resetComponents()
        ctgMsg.embed.title = "Subscribing to a VTuber"
        ctgMsg.embed.description = "Pick the VTuber's affiliation:"
        ctgMsg.embed.add_field(name="Searching for a specific VTuber?", value="Add the VTuber's name after the `subscribe` command.", inline=False)
        ctgMsg.addSelect(categories, placeholder="Select the VTuber's Affiliation")
        ctgMsg.addButton(2, "search", "Search for a VTuber", disabled=True)
        ctgMsg.addButton(2, "all", "Subscribe to all VTubers")
        ctgMsg.addButton(3, "cancel", "Cancel", style=discord.ButtonStyle.red)
    
        if isinstance(cmd, commands.Context):
            response = await ctgMsg.legacyPost(cmd)
        else:
            response = await ctgMsg.post(cmd, True, True)
        
        return response
    
    async def searchPick(cmd: Union[commands.Context, discord.Interaction], message: YagooMessage, searchTerm: str, searchResult: ChannelSearchResponse):
        """
        A prompt to pick possible search matches.
        
        Arguments
        ---
        cmd: Context or interaction from the invoked command.
        message: The message that will be used as the prompt.
        searchTerm: The search term by the user.
        searchResult: The `ChannelSearchResult` returned from searching for a channel.
        
        Returns
        ---
        `ChannelSearchResult`
        """
        choices = []
        
        message.resetMessage()
        message.embed.title = "Searching for a VTuber"
        message.embed.description = f"Displaying search results for: `{searchTerm}`\n"
        for item in searchResult.searchResults:
            choices.append(YagooSelectOption(item, item))
        message.addSelect(choices, "Select the search result here")
        message.addButton(2, "cancel", "Cancel", style=discord.ButtonStyle.red)
        
        if isinstance(cmd, commands.Context):
            result = await message.legacyPost(cmd)
        else:
            result = await message.post(cmd, True, True)
            
        if not result.responseType or result.buttonID == "cancel":
            searchResult.failed()
            return searchResult
    
        searchResult.matched()
        searchResult.channelName = result.selectValues[0]
        return searchResult
    
    async def displaySubbed(message: YagooMessage, subResult: SubscriptionResponse):
        """
        Gives a status to the user about subbed accounts.
        
        Arguments
        ---
        message: The message that will be used as the display.
        subResult: The `SubscriptionResponse` from the subscription prompts.
        """
        channels = ""
        message.resetEmbed()
        for name in subResult.channelNames:
            channels += f"{name}, "
        if subResult.subTypes:
            message.embed.title = "Successfully Subscribed!"
            message.embed.description = f"This channel is now subscribed to {channels.strip(', ')}."
            message.embed.color = discord.Colour.green()
            subTypes = ""
            for subType in subResult.subTypes:
                subTypes += f"{subType.capitalize()}, "
            message.embed.add_field(name="Subscription Types", value=subTypes.strip(", "))
        else:
            message.embed.title = "Already Subscribed!"
            message.embed.description = f"This channel is already subscribed to {channels.strip(', ')}!"
            message.embed.color = discord.Colour.red()
        message.msg = await message.msg.edit(content=None, embed=message.embed, view=None)
    
    class channelPick:
        async def parseToPages(category: dict):
            """
            Parses a category to pages for prompt consumption.
            
            Arguments
            ---
            category: The category as a `dict` containing `id` as the header, `name` as the sub-key.
            
            Returns
            ---
            A `list` of `YagooSelectOption`.
            """
            result = []
            
            for channel in category:
                result.append(YagooSelectOption(category[channel]["name"], channel))
            
            return result
        
        async def prompt(cmd: commands.Context, message: YagooMessage, category: dict, catName: str):
            """
            Prompts the user for which VTuber to pick.
            
            Arguments
            ---
            cmd: Context or interaction from the invoked command.
            msg: The message that will be used as the prompt.
            category: The category as a `dict` containing `id` as the header, `name` as the sub-key.
            catName: The name of the category.
            
            Returns
            ---
            An instance of `CategorySubscriptionResponse`
            """
            options = await subPrompts.channelPick.parseToPages(category)
            
            message.resetMessage()
            message.embed.title = f"Subscribing to {catName} VTubers"
            message.embed.description = "Pick a VTuber in the select below."
            message.embed.add_field(name="Not finding a VTuber in this category?",
                                    value="Search for a VTuber by adding the VTuber's name after the `subscribe` command.")
            message.addSelect(options, f"Pick the {catName} VTubers here", max_values=25)
            message.addButton(2, "all", f"Subscribe to all {catName} VTubers")
            message.addButton(3, "cancel", "Cancel", style=discord.ButtonStyle.red)
            
            if isinstance(cmd, commands.Context):
                response = await message.legacyPost(cmd)
            else:
                response = await message.post(cmd, True, True)
            
            if response.responseType:
                if response.responseType == "select":
                    return CategorySubscriptionResponse(True, catName, channelIDs=response.selectValues, channelData=category)
                if response.buttonID == "all":
                    return CategorySubscriptionResponse(True, catName, True)
            return CategorySubscriptionResponse(False)
    
    class subTypes:
        async def editMsg(subTypes: List[str], message: YagooMessage, buttonStates: dict, subText: str, subID: str, allowNone: bool):
            """Supplementary command to `subTypes.prompt`"""
            selected = False
            allTypes = True
            rowNum = 0
            for subType in subTypes:
                if buttonStates[subType]:
                    message.addButton(rowNum, subType, f"{subType.capitalize()} Notifications", style=discord.ButtonStyle.green)
                    selected = True
                else:
                    message.addButton(rowNum, subType, f"{subType.capitalize()} Notifications", style=discord.ButtonStyle.red)
                    allTypes = False
                rowNum += 1
            if allowNone:
                selected = True
            message.addButton(rowNum, "cancel", "Cancel", style=discord.ButtonStyle.red)
            if not allTypes:
                message.addButton(rowNum, "all", "Select All", style=discord.ButtonStyle.primary)
            else:
                message.addButton(rowNum, "all", "Select None", style=discord.ButtonStyle.grey)
            message.addButton(rowNum, subID, subText, style=discord.ButtonStyle.green, disabled=not selected)
        
        async def prompt(cmd: Union[commands.Context, discord.Interaction],
                         message: YagooMessage,
                         buttonText: str = "Subscribe",
                         buttonID: str = "subscribe",
                         subTypes: dict = None,
                         allowNone: bool = False):
            """
            Prompts the user for subscription types.
            The title and description must be set beforehand.
            
            Arguments
            ---
            ctx: Context from the executed command.
            msg: The message that will be used as the prompt.
            buttonText: The text for the subscribe button.
            buttonID: The ID for the subscribe button.
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
            
            while True:
                message.resetComponents()
                await subPrompts.subTypes.editMsg(subTypes, message, buttonStates, buttonText, buttonID, allowNone)
                if isinstance(cmd, commands.Context):
                    result = await message.legacyPost(cmd)
                else:
                    result = await message.post(cmd, True, True)
                
                if result.responseType:
                    if result.buttonID not in ["cancel", "all", buttonID]:
                        buttonStates[result.buttonID] = not buttonStates[result.buttonID]
                    elif result.buttonID == "all":
                        allBool = True
                        for button in buttonStates:
                            if allBool:
                                allBool = buttonStates[button]
                        for button in buttonStates:
                            buttonStates[button] = not allBool
                    else:
                        if result.buttonID == buttonID:
                            return SubscriptionData(buttonStates)
                        return result
                else:
                    return result
    
    class vtuberConfirm:
        async def prompt(cmd: Union[commands.Context, discord.Interaction], message: YagooMessage, title: str, action: str):
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
            message.resetMessage()
            message.embed.title = title
            if action.lower() == "unsubscribe":
                message.embed.description = "Are you sure you want to unsubscribe from this channel?"
            else:
                message.embed.description = f"Are you sure you want to {action} to this channel?"
            message.addButton(1, "cancel", "Cancel", style=discord.ButtonStyle.red)
            message.addButton(1, "results", "Search Results", style=discord.ButtonStyle.primary)
            message.addButton(1, "confirm", "Confirm", style=discord.ButtonStyle.green)
            
            if isinstance(cmd, commands.Context):
                result = await message.legacyPost(cmd)
            else:
                result = await message.post(cmd, True, True)
            
            return result

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
