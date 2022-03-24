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
from discord import app_commands
from discord.ext import commands
from yagoo.commands.general import botHelp, botTwt
from yagoo.commands.subscribe import defaultSubtype, subCategory, subCustom, sublistDisplay, unsubChannel
from yagoo.lib.botUtils import subPerms
from yagoo.lib.prompts import botError
from yagoo.types.error import InMaintenanceMode
from yagoo.types.message import YagooMessage
from yagoo.types.views import YagooSelectOption

class YagooSlash(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Slash commands cog loaded in!")
    
    @app_commands.command(name="help", description="List all commands under Yagoo bot")
    async def helpslash(self, interaction: discord.Interaction): # pylint: disable=redefined-builtin
        if self.bot.maintenance and not (interaction.user.id == self.bot.ownerID):
            raise InMaintenanceMode()
        await interaction.response.send_message(embed=await botHelp("/"), ephemeral=True)
    
    @helpslash.error
    async def helpslashError(self, interaction: discord.Interaction, error):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send(embed=await botError(interaction, self.bot, error), ephemeral=True)
    
    @app_commands.command(name="subscribe", description="Subscribes to the specified channel(s)")
    @app_commands.describe(channel='The YouTube channel to subscribe to')
    @app_commands.check(subPerms)
    async def subscribeSlash(self, interaction: discord.Interaction, channel: str = None):
        if self.bot.maintenance and not (interaction.user.id == self.bot.ownerID):
            raise InMaintenanceMode()
        await interaction.response.defer(ephemeral=True)
        if channel is None:
            await subCategory(interaction, self.bot)
        else:
            await subCustom(interaction, self.bot, channel)
    
    @subscribeSlash.error
    async def subscribeError(self, interaction: discord.Interaction, error):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send(embed=await botError(interaction, self.bot, error), ephemeral=True)
    
    @app_commands.command(name="unsubscribe", description="Unsubscribes from the specified channel(s)")
    @app_commands.describe(channel='The YouTube channel to unsubscribe from')
    @app_commands.check(subPerms)
    async def unsubscribeSlash(self, interaction: discord.Interaction, channel: str = None):
        if self.bot.maintenance and not (interaction.user.id == self.bot.ownerID):
            raise InMaintenanceMode()
        await interaction.response.defer(ephemeral=True)
        await unsubChannel(interaction, self.bot, channel)
    
    @unsubscribeSlash.error
    async def unsubscribeError(self, interaction: discord.Interaction, error):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send(embed=await botError(interaction, self.bot, error), ephemeral=True)
    
    @app_commands.command(name="subdefault", description="Sets the default channel subscription types")
    @app_commands.check(subPerms)
    async def subDefaultSlash(self, interaction: discord.Interaction):
        if self.bot.maintenance and not (interaction.user.id == self.bot.ownerID):
            raise InMaintenanceMode()
        await interaction.response.defer(ephemeral=True)
        await defaultSubtype(interaction, self.bot)
    
    @subDefaultSlash.error
    async def subDefaultSlashError(self, interaction: discord.Interaction, error):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send(embed=await botError(interaction, self.bot, error), ephemeral=True)
    
    @app_commands.command(name="sublist", description="List this channel's YouTube subscriptions")
    @app_commands.check(subPerms)
    async def sublistSlash(self, interaction: discord.Interaction):
        if self.bot.maintenance and not (interaction.user.id == self.bot.ownerID):
            raise InMaintenanceMode()
        await interaction.response.defer(ephemeral=True)
        await sublistDisplay(interaction, self.bot)
    
    @sublistSlash.error
    async def subListSlashError(self, interaction: discord.Interaction, error):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send(embed=await botError(interaction, self.bot, error), ephemeral=True)
    
    @app_commands.command(name="follow", description="Follow a Twitter account's tweets")
    @app_commands.describe(handle="The Twitter account's handle/username")
    @app_commands.check(subPerms)
    async def followSlash(self, interaction: discord.Interaction, handle: str):
        if self.bot.maintenance and not (interaction.user.id == self.bot.ownerID):
            raise InMaintenanceMode()
        await interaction.response.defer(ephemeral=True)
        await botTwt.follow(interaction, self.bot, handle)
    
    @followSlash.error
    async def followSlashError(self, interaction: discord.Interaction, error):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send(embed=await botError(interaction, self.bot, error), ephemeral=True)
    
    @app_commands.command(name="unfollow", description="Unfollow from any followed Twitter accounts")
    @app_commands.check(subPerms)
    async def unfollowSlash(self, interaction: discord.Interaction):
        if self.bot.maintenance and not (interaction.user.id == self.bot.ownerID):
            raise InMaintenanceMode()
        await interaction.response.defer(ephemeral=True)
        await botTwt.unfollow(interaction, self.bot)
    
    @unfollowSlash.error
    async def unfollowSlashError(self, interaction: discord.Interaction, error):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send(embed=await botError(interaction, self.bot, error), ephemeral=True)
    
    # POC: Recreation of subscription menu with new message class
    @app_commands.command(name="test", description="A test command.")
    @app_commands.guilds(751669314196602972)
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer()
        message = YagooMessage(self.bot, interaction.user,
                            "Subscribing to a VTuber", "Pick the VTuber's affiliation:",
                            color=discord.Color.from_rgb(32, 34, 37))
        message.embed.add_field(name="Action", value="Pick an entry in the list or use the buttons below for further actions.")
        selectOptions = []
        for i in range(1, 100):
            selectOptions.append(YagooSelectOption(str(i)))
        message.addSelect(selectOptions)
        message.addButton(3, "search", "Search for a VTuber")
        message.addButton(3, "all", "Subscribe to all VTubers")
        message.addButton(4, "cancel", "Cancel", style=discord.ButtonStyle.red)
        response = await message.post(interaction, True, True)
        print(vars(response))
        if response.selectValues:
            await message.msg.edit(content=f"You picked the option: `{response.selectValues[0]}`", embed=None, view=None)
        elif response.buttonID:
            await message.msg.edit(content=f"You picked the button: `{response.buttonID}`", embed=None, view=None)
        else:
            await message.msg.edit(content="The message timed out!", embed=None, view=None)

    @app_commands.command(name="modaltest", description="A modal test command.")
    @app_commands.guilds(751669314196602972)
    async def modalslash(self, interaction: discord.Interaction):
        modal = YagooMessage(self.bot, interaction.user, "Test Modal", "This is a test modal.")
        modal.addTextInput(label="Input 1", placeholder="Enter Something Here", text_id="input1")
        modal.addTextInput(label="Input 2", placeholder="Enter Something Here Also", text_id="input2", row=1)
        response = await modal.postModal(interaction)
        print(vars(response))
        await interaction.followup.send(content="Done!")
