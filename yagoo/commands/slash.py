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

import logging
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from .general import botGetInfo, botHelp, botTwt
from .subscribe import subCategory, subCustom, unsubChannel, sublistDisplay
from ..lib.dataUtils import botdb

class YagooSlash(commands.Cog):
    def __init__(self, bot, slash, prefix):
        self.bot = bot
        self.slash = slash
        self.prefix = prefix
        logging.info("Bot Slash Commands - Commands loaded!")
    
    @cog_ext.cog_slash(name="help", description="Shows the bot's help menu.", options=None)
    async def _help(self, ctx):
        db = await botdb.getDB()
        if await botdb.checkIfExists(str(ctx.guild.id), "server", "prefixes", db):
            prefix = (await botdb.getData(str(ctx.guild.id), "server", ("prefix",), "prefixes", db))["prefix"]
        else:
            prefix = self.prefix
        await ctx.send(embed=await botHelp(prefix))

    @cog_ext.cog_slash(name="info", description="Get information about a VTuber.",
                       options=[create_option(name = "name", description = "The VTuber's name to search for.", option_type = 3, required = True)])
    async def _info(self, ctx, name: str):
        await botGetInfo(ctx, self.bot, name)

    @cog_ext.cog_slash(name="subscribe", description="Subscribe to a VTuber's livestream/milestone notifications.",
                       options=[create_option(name = "name", description = "The VTuber's name that is being subscribed to.", option_type = 3, required = False)])
    async def _subscribe(self, ctx, name: str = None):
        if name is None:
            await subCategory(ctx, self.bot)
        else:
            await subCustom(ctx, self.bot, name)

    @cog_ext.cog_slash(name="sublist", description="Lists all the VTubers this channel is subscribed to.", options=None)
    async def _test(self, ctx):
        await sublistDisplay(ctx, self.bot)

    @cog_ext.cog_slash(name="unsubscribe", description="Unsubscribe to an existing VTuber's livestream/milestone notifications.",
                       options=[create_option(name = "name", description = "The VTuber's name that is being unsubscribed from.", option_type = 3, required = False)])
    async def _unsubscribe(self, ctx, name: str = None):
        await unsubChannel(ctx, self.bot, name)
    
    @cog_ext.cog_slash(name="follow", description="Follow a Twitter user to the channel.",
                       options=[create_option(name = "name", description = "The Twitter user's link or screen name.", option_type = 3, required = True)])
    async def _follow(self, ctx, name: str = None):
        await botTwt.follow(ctx, self.bot, name)

    @cog_ext.cog_slash(name="unfollow", description="Unfollow a Twitter user from the channel.", options=None)
    async def _unfollow(self, ctx):
        await botTwt.unfollow(ctx, self.bot)
