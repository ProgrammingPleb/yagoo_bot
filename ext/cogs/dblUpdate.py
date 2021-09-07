import dbl
import logging
from discord.ext import commands

class guildUpdate(commands.Cog):
    """Handles interactions with the top.gg API"""

    def __init__(self, bot, token):
        self.bot = bot
        self.token = token
        self.dblpy = dbl.DBLClient(self.bot, self.token, autopost=True) # Autopost will post your guild count every 30 minutes

    async def on_guild_post():
        logging.info("Discord Bot List - Server count posted successfully.")
