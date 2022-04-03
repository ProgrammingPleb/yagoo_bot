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
import tweepy
from typing import Optional, Union, List
from discord.ext import commands
from yagoo.lib.botVars import allSubTypes
from yagoo.types.data import CategorySubscriptionResponse, ChannelSearchResponse, ChannelSubscriptionData, ErrorReport, SubscriptionData, SubscriptionResponse, TwitterFollowData, TwitterUnfollowResponse, UnsubscriptionResponse, YouTubeChannel
from yagoo.types.message import YagooMessage
from yagoo.types.views import YagooSelectOption, YagooViewResponse

async def botError(cmd: Union[commands.Context, discord.Interaction],
                   bot: commands.Bot,
                   error: Union[commands.errors.CommandInvokeError, discord.app_commands.CommandInvokeError]):
    errEmbed = discord.Embed(title="An error has occurred!", color=discord.Colour.red())
    errReport = ErrorReport(cmd, error)
    
    if errReport.internal:
        errorTrace = ""
        for line in traceback.format_exception(type(error.original), error.original, error.original.__traceback__):
            errorTrace += line
        await bot.get_user(bot.owner_id).send("An internal error has occurred!"
                                              f"\nTraceback:```{errorTrace}```")
    
    if errReport.report:
        errEmbed.description = errReport.report
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

class refreshPrompts:
    async def confirm(cmd: Union[commands.Context, discord.Interaction],
                      message: YagooMessage):
        """
        Prompts the user if they want to refresh the channel's webhook.
        
        Arguments
        ---
        cmd: Context or interaction from the invoked command.
        message: The message used for the prompt.
        """
        message.embed.title = "Refreshing Channel Webhook"
        message.embed.description = "Are you sure you want to refresh this channel's webhook?"
        message.addButton(1, "no", "No", style=discord.ButtonStyle.red)
        message.addButton(1, "yes", "Yes", style=discord.ButtonStyle.green)
        
        if isinstance(cmd, commands.Context):
            return await message.legacyPost(cmd)
        return await message.post(cmd, True, True)

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
    
    async def displayProgress(message: YagooMessage):
        message.resetEmbed()
        message.embed.title = "Currently Subscribing..."
        message.embed.description = "Currently subscribing to the channels specified.\n" \
                                    "This might take longer if the amount of channels is larger."
        message.embed.color = discord.Color.from_rgb(0, 0, 0)
        message.msg = await message.msg.edit(content=None, embed=message.embed, view=None)
    
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
            `SubscriptionData` if the user confirmed the choice.
            `YagooViewResponse` if cancelled or timed out.
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
        async def parseToPages(server: ChannelSubscriptionData):
            """
            Parses the channel's subscriptions into pages that can be used by `pageNav.message`.
            
            Arguments
            ---
            server: The channel's subscription data.
            
            Returns
            ---
            A `list` of pages to be used as embed descriptions.
            """
            result: List[str] = []
            pos = 1
            text = ""
            for channel in server.allChannels:
                text += f"{pos}. {channel.channelName}\n"
                pos += 1
                if pos == 11:
                    result.append(text.strip())
                    pos = 1
                    text = ""
            if pos > 1:
                result.append(text.strip())
            return result
        
        async def prompt(cmd: Union[commands.Context, discord.Interaction], message: YagooMessage, pages: List[str], subData: ChannelSubscriptionData):
            """
            Show the user about the current subscriptions for the channel.
            
            Arguments
            ---
            ctx: Context or interaction from the invoked command.
            message: The message that will be used as the prompt.
            pages: A `list` containing the pages of the Discord channel's subscriptions.
            subData: The channel's subscription data.
            """
            message.embed.title = "Current Channel Subscriptions"
            pagePos = 0
            subFilter = []          # TODO: (LATER) Subscription filter after this update
            if len(pages) > 1:
                message.pages = len(pages)
                message.addPaginator(1)
            
            while True:
                message.embed.description = pages[pagePos]
                if isinstance(cmd, commands.Context):
                    result = await message.legacyPost(cmd)
                else:
                    result = await message.post(cmd, True, True)
                
                if result.responseType:
                    if result.buttonID == "next":
                        pagePos += 1
                    elif result.buttonID == "prev":
                        pagePos -= 1
                else:
                    break
            
            if len(subData.allChannels) > 1:
                message.embed.description = f"This channel is currently subscribed to {len(subData.allChannels)} channels."
            else:
                message.embed.description = f"This channel is currently subscribed to 1 channel."
            await message.msg.edit(content=None, embed=message.embed, view=None)

class unsubPrompts:
    class removePrompt:
        async def editMsg(message: YagooMessage, subTypes: dict):
            message.resetComponents()
            allSubs = True
            selected = False
            rowSort = {
                "livestream": 0,
                "milestone": 1,
                "premiere": 2,
                "twitter": 3
            }
            for subType in subTypes:
                if subTypes[subType]:
                    message.addButton(rowSort[subType], subType, f"{subType.capitalize()} Notifications", style=discord.ButtonStyle.green)
                    allSubs = False
                else:
                    message.addButton(rowSort[subType], subType, f"{subType.capitalize()} Notifications", style=discord.ButtonStyle.grey)
                    selected = True
            if not allSubs:
                message.addButton(4, "cancel", "Cancel", style=discord.ButtonStyle.red)
                message.addButton(4, "select", "Select All")
                message.addButton(4, "submit", "Unsubscribe", style=discord.ButtonStyle.green, disabled=not selected)
            else:
                message.addButton(4, "cancel", "Cancel", style=discord.ButtonStyle.red)
                message.addButton(4, "select", "Select None", style=discord.ButtonStyle.grey)
                message.addButton(4, "submit", "Unsubscribe", style=discord.ButtonStyle.green, disabled=not selected)

        async def parseToChannels(channelIDs: List[str], subData: ChannelSubscriptionData):
            result: List[YouTubeChannel] = []
            
            for channelID in channelIDs:
                result.append(subData.findChannel(channelID))
            
            return result
        
        async def prompt(cmd: Union[commands.Context, discord.Interaction],
                         message: YagooMessage,
                         channelIDs: Optional[List[str]] = None,
                         subData: Optional[ChannelSubscriptionData] = None,
                         allChannels: bool = False):
            """
            Prompts the user for which subscription type to unsubscribe from.
            
            Arguments
            ---
            ctx: Context from the executed command.
            msg: The message that will be used as the prompt.
            channelIDs: IDs of the VTuber channels to be unsubscribed from.
            subData: The subscription data of the current channel.
            allChannels: If all channels are to be unsubscribed.
            
            Returns
            ---
            A `dict` with:
            - status: `True` if an option was chosen by the user.
            - unsubbed: A `list` with subscription types to unsubscribe from.
            """
            if not allChannels:
                channels = await unsubPrompts.removePrompt.parseToChannels(channelIDs, subData)
            else:
                channels = subData.allChannels
            subTypes = {}
            
            if allChannels:
                name = "All Channels"
            elif len(channelIDs) > 1:
                name = "Multiple Channels"
            else:
                name = channels[0].channelName
            message.resetEmbed()
            message.embed.title = f"Unsubscribing from {name}"
            message.embed.description = "Choose the subscription types to unsubscribe from."
            
            if not allChannels:
                for channel in channels:
                    for subType in subData.findTypes(channel.channelID):
                        if subType not in subTypes:
                            subTypes[subType] = True
            else:
                for subType in allSubTypes(False):
                    subTypes[subType] = True
            
            while True:
                await unsubPrompts.removePrompt.editMsg(message, subTypes)
                if isinstance(cmd, commands.Context):
                    result = await message.legacyPost(cmd)
                else:
                    result = await message.post(cmd, True, True)
                
                if result.responseType:
                    if result.buttonID == "cancel":
                        return UnsubscriptionResponse(False)
                    if result.buttonID == "submit":
                        unsubbed = []
                        for subType in subTypes:
                            if not subTypes[subType]:
                                unsubbed.append(subType)
                        return UnsubscriptionResponse(True, unsubbed, channels)
                    if result.buttonID == "select":
                        allSubs = True
                        for subType in subTypes:
                            if subTypes[subType]:
                                allSubs = False
                        for subType in subTypes:
                            subTypes[subType] = allSubs
                    else:
                        subTypes[result.buttonID] = not subTypes[result.buttonID]
                else:
                    return UnsubscriptionResponse(False)

    async def displayResult(message: YagooMessage, unsubData: UnsubscriptionResponse):
        """
        Displays the unsubscription result.
        
        message: The message used to display the result.
        unsubData: The unsubscription data.
        """
        subTypeText = ""
        channels = ""
        
        for subType in unsubData.subTypes:
            subTypeText += f"{subType.capitalize()}, "
        
        if len(unsubData.channels) <= 5:
            for channel in unsubData.channels:
                channels += f"{channel.channelName}, "
        else:
            channels = f"{len(unsubData.channels)} channels"
        
        message.resetEmbed()
        message.embed.title = "Successfully Unsubscribed!"
        message.embed.description = f"This channel is now unsubscribed from {channels.strip(', ')}."
        message.embed.color = discord.Color.green()
        message.embed.add_field(name="Subscription Types", value=subTypeText.strip(", "), inline=False)
        message.msg = await message.msg.edit(content=None, embed=message.embed, view=None)
        return

class TwitterPrompts:
    class follow:
        async def confirm(cmd: Union[commands.Context, discord.Interaction], message: YagooMessage, twtUser: tweepy.User):
            """
            Asks for confirmation of following the Twitter account that was requested.
            
            Arguments
            ---
            cmd: Context or interaction from the invoked command.
            message: The message used to display the confirmation.
            twtUser: The Twitter account.
            """
            message.embed.title = f"Following {twtUser.name} to this channel"
            message.embed.description = "Do you want to follow this Twitter account?"
            message.addButton(1, "cancel", "Cancel", style=discord.ButtonStyle.red)
            message.addButton(1, "confirm", "Confirm", style=discord.ButtonStyle.green)
            
            if isinstance(cmd, commands.Context):
                result = await message.legacyPost(cmd)
            else:
                result = await message.post(cmd, True, True)
            
            return result
        
        def displayResult(message: YagooMessage, accName: str, status: bool):
            """
            Display the result of the follow action.
            
            Arguments
            ---
            message: The message used to display the result.
            accName: The Twitter account name.
            status: The status from the follow command.
            """
            message.resetEmbed()
            if status:
                message.embed.title = "Successfully Followed Account!"
                message.embed.description = f"This channel is now following @{accName}."
                message.embed.color = discord.Color.green()
            else:
                message.embed.title = "Already Followed Account!"
                message.embed.description = f"This channel is already following @{accName}."
                message.embed.color = discord.Color.red()
    
    class unfollow:
        async def parse(followed: list, data: dict):
            """
            Parses a list of followed Twitter accounts.
            
            Arguments
            ---
            followed: A `list` containing the Twitter accounts followed in the Discord channel.
            data: A `dict` containing the Twitter custom accounts data.
            
            Returns
            ---
            `TwitterFollowData`.
            """
            follows = TwitterFollowData(True)
            
            for twtID in followed:
                follows.addAccount(twtID, data[twtID]["screenName"], data[twtID]["name"])
            
            return follows
        
        async def prompt(cmd: Union[commands.Context, discord.Interaction],
                         message: YagooMessage,
                         followData: TwitterFollowData):
            """
            Prompts the user for which Twitter accounts to be unfollowed.
            
            Arguments
            ---
            cmd: Context or interaction from the invoked command.
            msg: The message that will be used as the prompt.
            options: The Discord channel's Twitter follows.
            
            Returns
            ---
            `TwitterUnfollowResponse`
            """
            response = TwitterUnfollowResponse(False)
            
            message.resetMessage()
            message.embed.title = "Unfollowing from Twitter Accounts"
            message.embed.description = "Choose the account(s) to be unfollowed."
            message.embed.add_field(name="Note seeing the Twitter account on this list?",
                                    value="Twitter accounts followed through the `subscribe` command "
                                          "will need to be unfollowed through the `unsubscribe` command.")
            
            options = []
            for account in followData.accounts:
                options.append(YagooSelectOption(account.name, account.accountID, f"@{account.handle}"))
            message.addSelect(options, "Pick the Twitter account(s) here", max_values=25)
            message.addButton(3, "all", "Unfollow from all Twitter Channels")
            message.addButton(4, "cancel", "Cancel", style=discord.ButtonStyle.red)
            
            if isinstance(cmd, commands.Context):
                result = await message.legacyPost(cmd)
            else:
                result = await message.post(cmd, True, True)
            
            if result.responseType:
                if result.selectValues:
                    response.status = True
                    for handle in result.selectValues:
                        account = followData.findAccount(handle)
                        response.addAccount(account.accountID, account.handle, account.name)
                elif result.buttonID == "all":
                    response.status = True
                    response.allAccounts = True
            return response

        def displayResult(message: YagooMessage, unfollowData: TwitterUnfollowResponse):
            """
            Display the result of the follow action.
            
            Arguments
            ---
            message: The message used to display the result.
            unfollowData: The channel's unfollow data.
            """
            message.resetEmbed()
            message.embed.title = "Successfully Unfollowed Accounts!"
            message.embed.color = discord.Color.green()
            
            accounts = ""
            if len(unfollowData.accounts) <= 3:
                for account in unfollowData.accounts:
                    accounts += f"@{account.handle}, "
            else:
                accounts = f"{len(unfollowData.accounts)} accounts'"
            if unfollowData.allAccounts:
                accounts = "all Twitter accounts'"
            message.embed.description = f"The channel has been unfollowed from {accounts.strip(', ')} tweets."
