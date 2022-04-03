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
from .views import YagooModal, YagooSelectOption, YagooTextInput, YagooView, YagooButton, YagooSelect
from .error import ButtonNotFound, ButtonReserved, NoSelectValues, RowFull

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
        
        Note
        ---
        If an external page count is used, set the `pages` attribute first.
        Current page indicator will be handled internally.
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
                  options: List[YagooSelectOption] = [],
                  placeholder: str = "",
                  min_values: int = 1,
                  max_values: int = 1):
        """
        Adds a select to the message. Will automatically add a paginator if required.
        It is advised to leave a row for the paginator. The select will also be added to the first row.
        
        Arguments
        ---
        options: A `list` of `YagooSelectOption` containing the options for the select.
        select_id: The ID of the select.
        placeholder: The placeholder text for the select when no options are selected.
        min_values: Minimum amount of options to be selected.
        max_values: Maximum amount of options to be selected.
        """
        singlePage = []
        if len(options) == 0:
            raise NoSelectValues()
        for option in options:
            singlePage.append(option)
            if len(singlePage) == 25:
                self.pageData.append(singlePage)
                self.pages += 1
                singlePage = []
        if singlePage != []:
            self.pageData.append(singlePage)
            self.pages += 1
        self.select = YagooSelect(placeholder, min_values, max_values, self.pageData[0], 0)
        
        if self.pages > 1:
            self.addPaginator(1)
        else:
            if len(self.select.options) < max_values:
                self.select.max_values = len(self.select.options)
    
    def addTextInput(self,
                     text_id: str = "text",
                     label: str = "Label",
                     style: discord.TextStyle = discord.TextStyle.short,
                     placeholder: str = "Placeholder Text",
                     default: str = None,
                     required: bool = False,
                     min_length: int = None,
                     max_length: int = None,
                     row: int = 0):
        """
        Adds a text input to the message.
        
        Arguments
        ---
        id: The ID of the select.
        label: The label for the text input box.
        style: The style of the text input box. (`short` or `long`)
        placeholder: The placeholder text for the text input when no text is in the input box.
        default: The default text that will be in the input box.
        required: Whether an input is required from the user.
        min_length: Minimum length for the text input.
        max_length: Maximum amount of options to be selected.
        row: The row to add the select to.
        """
        if self.textFields:
            for field in self.textFields:
                if row == field.row:
                    raise RowFull(field.custom_id, row)
        self.textFields.append(YagooTextInput(text_id, label, style, placeholder, default, required, min_length, max_length, row))
    
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
        self.textFields = []
        self.pageData = []
        self.pages = 0
        self.currentPage = 1
    
    def resetEmbed(self):
        """
        Resets the embed of the message.
        """
        self.embed.clear_fields()
        self.embed.title = ""
        self.embed.description = ""
        self.embed.color = discord.Color.blurple()
        self.embed.url = None
        self.embed.set_image(url=None)
        self.embed.set_thumbnail(url=None)
        self.embed.remove_author()
        self.embed.remove_footer()
    
    def resetMessage(self):
        """
        Resets the message.
        """
        self.resetComponents()
        self.resetEmbed()
    
    async def legacyPost(self, ctx: commands.Context):
        """
        Post the message (or edit if it is an existing message) to the channel that invoked the command.
        
        Arguments
        ---
        ctx: The context that originated from the command.
        
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
        else:
            self.msg = await self.msg.edit(content=None, embed=self.embed, view=self.view)
        self.view.responseData.message = self.msg
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
                        self.msg = await self.msg.edit(content=None, embed=self.embed, view=self.view)
                        if self.select:
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
        else:
            self.msg = await self.msg.edit(content=None, embed=self.embed, view=self.view)
        self.view.responseData.message = self.msg
        while True:
            response = await self.wait_for_response()
            if response:
                if self.pages > 1:
                    if self.view.responseData.buttonID in ("next", "prev"):
                        if self.view.responseData.buttonID == "next":
                            self.paginatorUpdate(True)
                        elif self.view.responseData.buttonID == "prev":
                            self.paginatorUpdate(False)
                        self.msg = await self.msg.edit(content=None, embed=self.embed, view=self.view)
                        if self.select:
                            self.view.responseData.clear()
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
        self.msg = await self.msg.edit(view=None)
        self.view.stop()
    
    # Internal functions start here
    async def wait_for_response(self, timeout: int = 60):
        """Waits for a response from the message components. Should only be used inside `message.py`."""
        def check(interaction: discord.Interaction):
            if interaction.message:
                return interaction.user.id == self.user.id and interaction.message.id == self.msg.id
            return False
        
        try:
            await self.bot.wait_for("interaction", check=check, timeout=timeout)
        except asyncio.TimeoutError:
            return False
        return True

    def paginatorUpdate(self, nextPage: bool):
        """
        Updates the select and paginator to it's respective state. Should only be used inside `message.py`.
        
        Arguments
        ---
        next: Indicate if the next page button is clicked. False will indicate for the previous page button instead.
        """
        if nextPage:
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
        
        if self.select:
            self.select.options = self.pageData[self.currentPage - 1]
            if self.select.absoluteMax < len(self.select.options):
                self.select.max_values = self.select.absoluteMax
            elif self.select.absoluteMax >= len(self.select.options):
                self.select.max_values = len(self.select.options)
            self.view.rebuild(self.buttons, self.select)
