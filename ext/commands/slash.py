import logging
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import create_option
from .general import botGetInfo, botHelp, botSublist, botUnsub
from ..share.botUtils import subPerms
from .subscribe import subCategory, subCustom

class YagooSlash(commands.Cog):
    def __init__(self, bot, slash):
        self.bot = bot
        self.slash = slash
        logging.info("Bot Slash Commands - Commands loaded!")
    
    @cog_ext.cog_slash(name="help", description="Shows the bot's help menu.", options=None)
    async def _help(self, ctx):
        await ctx.send(embed=await botHelp())
    
    @cog_ext.cog_slash(name="test", description="A test command. This should not be available to the end user!", options=None)
    async def _test(self, ctx):
        await ctx.send("Test command is working!")

    @cog_ext.cog_slash(name="info", description="Get information about a VTuber.",
                       options=[create_option(name = "name", description = "The VTuber's name to search for.", option_type = 3, required = True)],
                       guild_ids=[802863586510241814, 751669314196602972])
    async def _info(self, ctx, name: str):
        await botGetInfo(ctx, self.bot, name)

    @cog_ext.cog_slash(name="subscribe", description="Subscribe to a VTuber's livestream/milestone notifications.",
                       options=[create_option(name = "name", description = "The VTuber's name that is being subscribed to.", option_type = 3, required = False)],
                       guild_ids=[802863586510241814, 751669314196602972])
    async def _sub(self, ctx, name: str = None):
        if name is None:
            await subCategory(ctx, self.bot)
        else:
            await subCustom(ctx, self.bot, name)

    @cog_ext.cog_slash(name="sublist", description="Lists all the VTubers this channel is subscribed to.", options=None)
    async def _test(self, ctx):
        await botSublist(ctx, self.bot)

    @cog_ext.cog_slash(name="unsubscribe", description="Unsubscribe to an existing VTuber's livestream/milestone notifications.", options=None)
    async def _unsub(self, ctx):
        await botUnsub(ctx, self.bot)
