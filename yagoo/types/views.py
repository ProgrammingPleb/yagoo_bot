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
from typing import List, Union, Optional
from yagoo.types.error import ValueTooLong

class YagooViewResponse():
    """Used for interaction responses from the user. Should not be called outside of this `view.py`."""
    def __init__(self):
        self.message: Union[discord.Message, discord.WebhookMessage] = None
        self.responseType: str = None
        self.buttonID: int = None
        self.selectValues: list = None
        self.textValues: dict = None
    
    def clear(self):
        """Clears the variables in the view response."""
        self.message = None
        self.responseType = None
        self.buttonID = None
        self.selectValues = None
        self.textValues: str = None

class YagooButton(discord.ui.Button):
    """A button used for Yagoo Bot messages. Cannot be used by itself."""
    def __init__(self, id: str, label: str, url: str, style: discord.ButtonStyle, disabled: bool, row: int):
        super().__init__(style=style, custom_id=id, label=label, url=url, disabled=disabled, row=row)
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: YagooView = self.view
        view.responseData.responseType = "button"
        view.responseData.buttonID = self.custom_id
        await interaction.response.defer()

class YagooSelect(discord.ui.Select):
    """A select used for Yagoo Bot messages. Cannot be used by itself."""
    def __init__(self, placeholder: str,
                 min_values: int, max_values: int, options: List[discord.SelectOption], row: int):
        super().__init__(placeholder=placeholder, min_values=min_values, max_values=max_values, options=options, row=row)
        self.absoluteMax = max_values
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: YagooView = self.view
        view.responseData.responseType = "select"
        view.responseData.selectValues = self.values
        await interaction.response.defer()

class YagooSelectOption(discord.SelectOption):
    def __init__(self,
                 label: str,
                 value: Optional[str] = None,
                 description: Optional[str] = None,
                 default: Optional[bool] = False):
        if len(label) > 100:
            label = f"{label[0:97]}..."
        
        if not value:
            value = label.lower()
        
        if len(value) > 100:
            raise ValueTooLong(value)
        
        super().__init__(label=label, value=value, description=description, default=default)

class YagooTextInput(discord.ui.TextInput):
    """A text input box used for Yagoo Bot messages. Cannot be used by itself."""
    def __init__(self, id: str,
                 label: str,
                 style: discord.TextStyle,
                 placeholder: str,
                 default: str,
                 required: bool,
                 min_length: int,
                 max_length: int,
                 row: int):
        super().__init__(custom_id=id, label=label, style=style, placeholder=placeholder, default=default, required=required, min_length=min_length, max_length=max_length, row=row)

class YagooView(discord.ui.View):
    """A view UI used for Yagoo Bot messages. Cannot be used by itself."""
    def __init__(self, buttons: list = None, select: discord.ui.Select = None):
        super().__init__()
        self.responseData = YagooViewResponse()

        if buttons:
            for button in buttons:
                self.add_item(button)
        
        if select:
            self.add_item(select)
    
    def rebuild(self, buttons: list = None, select: discord.ui.Select = None):
        """
        Rebuilds the existing view with new components.
        
        Arguments
        ---
        buttons: A `list` of buttons for the view.
        select: The select object for the view.
        """
        self.clear_items()
        
        if buttons:
            for button in buttons:
                self.add_item(button)
        
        if select:
            self.add_item(select)

class YagooModal(discord.ui.Modal):
    """A modal used for Yagoo Bot messages. Cannot be used by itself."""
    def __init__(self, title: str, text: List[discord.ui.TextInput]):
        super().__init__(title=title)
        self.ready = False
        self.responseData = YagooViewResponse()

        if text:
            for field in text:
                self.add_item(field)
    
    async def on_submit(self, interaction: discord.Interaction):
        self.ready = True
        self.responseData.textValues = {}
        for field in interaction.data["components"]:
            if field["components"][0]["value"]:
                self.responseData.textValues[field["components"][0]["custom_id"]] = field["components"][0]["value"]
