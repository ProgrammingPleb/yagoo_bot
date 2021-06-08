import logging
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from .general import botGetInfo, botHelp, botSublist, botTwt, botUnsub
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
        await botSublist(ctx, self.bot)

    @cog_ext.cog_slash(name="unsubscribe", description="Unsubscribe to an existing VTuber's livestream/milestone notifications.", options=None)
    async def _unsubscribe(self, ctx):
        await botUnsub(ctx, self.bot)
    
    @cog_ext.cog_slash(name="follow", description="Follow a Twitter user to the channel.",
                       options=[create_option(name = "name", description = "The Twitter user's link or screen name.", option_type = 3, required = True)])
    async def _follow(self, ctx, name: str = None):
        await botTwt.follow(ctx, self.bot, name)

    @cog_ext.cog_slash(name="unfollow", description="Unfollow a Twitter user from the channel.", options=None)
    async def _unfollow(self, ctx):
        await botTwt.unfollow(ctx, self.bot)
