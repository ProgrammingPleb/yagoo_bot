import aiohttp
import discord
from discordTogether import DiscordTogether
from bs4 import BeautifulSoup
from discord.ext import commands
from ..lib.dataUtils import botdb, dbTools

class customCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ytTogether = DiscordTogether(bot)
    
    def tempuraCheck(ctx: commands.Context):
        if ctx.guild.id in [616469346323005463, 751669314196602972, 637518305070153728, 789053534075224064]:
            return True
        return False
    
    @commands.command()
    @commands.check(tempuraCheck)
    async def ytogether(self, ctx: commands.Context, vcID: str = None):
        try:
            if not vcID:
                link = await self.ytTogether.create_link(ctx.author.voice.channel.id, 'youtube')
            else:
                link = await self.ytTogether.create_link(vcID, 'youtube')
            await ctx.message.add_reaction("\U0001F4EB")
            return await ctx.author.send(f"Click the link below to use the `YouTube Together` feature!\n{link}")
        except Exception as e:
            await ctx.message.add_reaction("\U0000274C")
    
    @commands.command()
    @commands.check(tempuraCheck)
    async def maimai(self, ctx: commands.Context):
        db = await botdb.getDB()
        webhook = await dbTools.serverGrab(self.bot, ctx.guild.id, ctx.channel.id, ("url",), db)
        embed = discord.Embed(title="maimai DX Locations", color=0x464eba)
        oneutama = False
        putra = False
        async with aiohttp.ClientSession() as session:
            async with session.get("https://location.am-all.net/alm/location?gm=98&lang=en&ct=1004") as r:
                if "設置店舗がありません。" in await r.text():
                    embed.description = "No locations are currently open."
                else:
                    page = BeautifulSoup(await r.text(), "html5lib")
                    locData = page.find("div", {"class": "content_box"})
                    locQty = locData.find('h3').find_all('span')[1].text
                    locQty = int(locQty.split(" ")[0])
                    if locQty == 1:
                        locQtyCont = "location is currently open. <:aaaaaaaaaaaaaaaa:744596625942511706>"
                    elif locQty < 5:
                        locQtyCont = "locations are currently open. <:aaaaaaaaaaaaaaaa:744596625942511706>"
                    else:
                        locQtyCont = "locations are currently open."
                    embed.description = f"{locQty} {locQtyCont}"
                    locPlaces = locData.find("ul", {"class": "store_list"}).find_all("li")
                    
                    for place in locPlaces:
                        locName = place.find("span", {"class": "store_name"}).text
                        if "SUNWAY PUTRA" in locName:
                            putra = True
                        if ("CROSS FIRE" in locName) or ("CROSSFIRE" in locName):
                            oneutama = True
                        locAddr = place.find("span", {"class": "store_address"}).text
                        locLinkPart = place.find("span", {"class": "store_bt"}) \
                                    .find("button")["onclick"] \
                                    .replace("location.href='", "") \
                                    .replace("'; return false;", "")
                        locLink = f"https://location.am-all.net/alm/{locLinkPart}"
                        embed.add_field(name=locName, value=f"{locAddr}\n[Store Details]({locLink})", inline=False)
                    
                    if not putra:
                        embed.add_field(name="Sunway Putra", value="Still haven't opened yet <:pepe_cry:806500678201114634>", inline=False)
                    if not oneutama:
                        embed.add_field(name="One Utama", value="Still haven't opened yet <:pepe_cry:806500678201114634>", inline=False)

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook["url"], adapter=discord.AsyncWebhookAdapter(session))
            await webhook.send(embed=embed, username="ALL.Net Store Locator", avatar_url="https://img.pleb.moe/2021/0909/10-09-30.jpg")
