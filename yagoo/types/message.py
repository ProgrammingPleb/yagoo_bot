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
import discord
from typing import List
from discord.ext import commands
from .views import YagooModal, YagooTextInput, YagooView, YagooButton, YagooSelect
from .error import ButtonNotFound, ButtonReserved

class YagooMessage():
    """
    A message to be used by the Yagoo bot.
    
    Reserved button IDs = prev, pageid, next, cancel
    (cancel is only reserved when a select is used.)
    """
    def __init__(self, bot: commands.Bot,
                 user: discord.User,
                 title: str = "",
                 description: str = "",
                 image: str = None,
                 color: discord.Color = discord.Color.blurple()) -> None:
        self.bot: commands.Bot = bot
        self.user: discord.User = user
        self.embed: discord.Embed = discord.Embed(title=title, description=description, color=color)
        self.image: str = image
        self.color: discord.Color = color
        self.view: YagooView = None
        self.modal: YagooModal = None
        self.buttons: List[YagooButton] = []
        self.select: YagooSelect = None
        self.textFields: List[YagooTextInput] = []
        self.pageData: list = []
        self.pages: int = 0
        self.currentPage: int = 1
        self.msg: discord.Message = None
    
    def addButton(self, row: int = 1,
                        button_id: str = "",
                        label: str = "",
                        url: str = None,
                        style: discord.ButtonStyle = discord.ButtonStyle.primary,
                        disabled: bool = False):
        """
        Adds a button to the message.
        
        Arguments
        ---
        row: The row to add the button to. (Good practice is to use row 1 and onwards)
        text: The text for the button.
        url: The URL that this button redirects to.
        label: The label used for determining the button that is clicked.
        color: The color of the button.
        disabled: Whether or not the button should be disabled.
        """
        if button_id in ("prev", "next", "pageid"):
            raise ButtonReserved(button_id)
        self.buttons.append(YagooButton(button_id, label, url, style, disabled, row))
    
    def addPaginator(self, row: int = 1):
        """
        Adds a paginator to the message.
        
        Arguments
        ---
        row: The row to add the paginator to.
        pageData: A `list` containing the current page as the first object and the total number of pages as the second object.
        """
        # Check if any buttons are on the rows before the paginator row
        maxRow = 0
        for button in self.buttons:
            if button.row <= row and (row - button.row + 1 > maxRow):
                maxRow = row - button.row + 1
        
        # Move all existing buttons to the other row if any button is on those rows
        if maxRow > 0:
            for button in self.buttons:
                button.row += maxRow
        
        self.buttons.append(YagooButton("prev", "⬅️", None, discord.ButtonStyle.blurple, True, 1))
        self.buttons.append(YagooButton("pageid", f"Page {self.currentPage}/{self.pages}", None, discord.ButtonStyle.grey, True, 1))
        if self.pages > 1:
            self.buttons.append(YagooButton("next", "➡️", None, discord.ButtonStyle.blurple, False, 1))
        else:
            self.buttons.append(YagooButton("next", "➡️", None, discord.ButtonStyle.blurple, True, 1))
    
    def addSelect(self,
                  options: List[dict] = [],
                  select_id: str = "select",
                  placeholder: str = "",
                  min_values: int = 1,
                  max_values: int = 1):
        """
        Adds a select to the message. Will automatically add a paginator if required.
        It is advised to leave a row for the paginator. The select will also be added to the first row.
        
        Arguments
        ---
        options: A `list` of `dict`s containing the options for the select.
        select_id: The ID of the select.
        placeholder: The placeholder text for the select when no options are selected.
        min_values: Minimum amount of options to be selected.
        max_values: Maximum amount of options to be selected.
        
        Options Format
        ---
        label: The label that is displayed to the users.
        value: The value that is returned when the option is selected. (Optional)
        """
        def lengthCheck(string: str):
            """Checks the string length if it's above 100 characters."""
            if len(string) > 100:
                return f"{string[0:97]}..."
            return string
        
        singlePage = []
        for option in options:
            if "value" in option:
                optObject = discord.SelectOption(label=lengthCheck(option["label"]), value=option["value"])
            else:
                optObject = discord.SelectOption(label=lengthCheck(option["label"]), value=option["label"])
            singlePage.append(optObject)
            if len(singlePage) == 25:
                self.pageData.append(singlePage)
                self.pages += 1
                singlePage = []
        if singlePage != []:
            self.pageData.append(singlePage)
            self.pages += 1
        self.select = YagooSelect(select_id, placeholder, min_values, max_values, self.pageData[0], 0)
        
        if self.pages > 1:
            self.addPaginator(1)
    
    def editButton(self, button_id: str,
                         label: str = None,
                         url: str = None,
                         style: discord.ButtonStyle = None,
                         disabled: bool = None):
        """
        Edits a button on the message.
        
        Arguments
        ---
        text: The text for the button.
        url: The URL that this button redirects to.
        label: The label used for determining the button that is clicked.
        color: The color of the button.
        disabled: Whether or not the button should be disabled.
        """
        found = False
        for button in self.buttons:
            if button.custom_id == button_id:
                found = True
                if label:
                    button.label = label
                if url:
                    button.url = url
                if style:
                    button.style = style
                if disabled is not None:
                    button.disabled = disabled
        
        if not found:
            raise ButtonNotFound(button_id)
    
    def resetComponents(self):
        """
        Removes all the components from the message.
        """
        self.buttons = []
        self.select = None
        self.pageData = []
        self.pages = 1
        self.currentPage = 1
    
    async def legacyPost(self, ctx: commands.Context, ephemeral: bool = False):
        """
        Post the message (or edit if it is an existing message) to the channel that invoked the command.
        
        Arguments
        ---
        interaction: The context that originated from the command.
        ephemeral: Whether the posted message should be ephemeral.
        
        Returns
        ---
        A `dict` with:
        - type: The interaction type (button, select)
        - buttonID: The ID of the button that was clicked. (Only if type is `button`)
        - selectData: The data from the select. (Only if type is `select`)
        """
        self.view = YagooView(self.buttons, self.select)
        if not self.msg:
            self.msg = await ctx.send(embed=self.embed, view=self.view)
            self.view.responseData.message = self.msg
        else:
            await self.msg.edit(embed=self.embed, view=self.view)
        while True:
            response = await self.wait_for_response()
            if response:
                if self.pages > 1:
                    if self.view.responseData.buttonID in ("next", "prev"):
                        if self.view.responseData.buttonID == "next":
                            self.paginatorUpdate(True)
                        elif self.view.responseData.buttonID == "prev":
                            self.paginatorUpdate(False)
                        self.view.responseData.clear()
                        await self.msg.edit(embed=self.embed, view=self.view)
                        continue
            return self.view.responseData
    
    async def post(self, interaction: discord.Interaction, followup: bool = False, ephemeral: bool = False):
        """
        Post the message (or edit if it is an existing message) to the channel that invoked the command.
        
        Arguments
        ---
        interaction: The Discord interaction that originated from the command.
        followup: Whether the posted message should be a followup to the invoked command.
        ephemeral: Whether the posted message should be ephemeral.
        
        Returns
        ---
        A `dict` with:
        - type: The interaction type (button, select)
        - buttonID: The ID of the button that was clicked. (Only if type is `button`)
        - selectData: The data from the select. (Only if type is `select`)
        """
        self.view = YagooView(self.buttons, self.select)
        if not self.msg:
            if followup:
                self.msg = await interaction.followup.send(embed=self.embed, view=self.view, ephemeral=ephemeral)
            else:
                self.msg = await interaction.channel.send(embed=self.embed, view=self.view, ephemeral=ephemeral)
            self.view.responseData.message = self.msg
        else:
            await self.msg.edit(embed=self.embed, view=self.view)
        while True:
            response = await self.wait_for_response()
            if response:
                if self.pages > 1:
                    if self.view.responseData.buttonID in ("next", "prev"):
                        if self.view.responseData.buttonID == "next":
                            self.paginatorUpdate(True)
                        elif self.view.responseData.buttonID == "prev":
                            self.paginatorUpdate(False)
                        self.view.responseData.clear()
                        await self.msg.edit(embed=self.embed, view=self.view)
                        continue
            return self.view.responseData
    
    async def postModal(self, interaction: discord.Interaction):
        """
        Post the modal to the channel that invoked the command.
        
        Arguments
        ---
        interaction: The Discord interaction that originated from the command.
        followup: Whether the posted message should be a followup to the invoked command.
        ephemeral: Whether the posted message should be ephemeral.
        
        Returns
        ---
        A `dict` with:
        - type: The interaction type (button, select)
        - buttonID: The ID of the button that was clicked. (Only if type is `button`)
        - selectData: The data from the select. (Only if type is `select`)
        """
        self.modal = YagooModal(self.embed.title, self.textFields)
        await interaction.response.send_modal(self.modal)
        while True:
            if self.modal.ready:
                return self.modal.responseData
            await asyncio.sleep(0.25)
    
    async def stop(self):
        """
        Stops receiving any input from the components in the message. Cannot be undone.
        """
        await self.msg.edit(view=None)
        self.view.stop()
    
    # Internal functions start here
    async def wait_for_response(self, timeout: int = 60):
        """Waits for a response from the message components. Should only be used inside `message.py`."""
        def check(interaction: discord.Interaction):
            return interaction.user.id == self.user.id and interaction.message.id == self.msg.id
        
        try:
            await self.bot.wait_for("interaction", check=check, timeout=timeout)
        except asyncio.TimeoutError:
            return False
        return True

    def paginatorUpdate(self, next: bool):
        """
        Updates the select and paginator to it's respective state. Should only be used inside `message.py`.
        
        Arguments
        ---
        next: Indicate if the next page button is clicked. False will indicate for the previous page button instead.
        """
        if next:
            self.currentPage += 1
        else:
            self.currentPage -= 1
        
        if self.currentPage == 1:
            self.editButton("prev", disabled=True)
            self.editButton("next", disabled=False)
        elif self.currentPage == self.pages:
            self.editButton("prev", disabled=False)
            self.editButton("next", disabled=True)
        else:
            self.editButton("prev", disabled=False)
            self.editButton("next", disabled=False)
        self.editButton("pageid", label=f"Page {self.currentPage}/{self.pages}")
        
        self.select.options = self.pageData[self.currentPage - 1]
        self.view.rebuild(self.buttons, self.select)
