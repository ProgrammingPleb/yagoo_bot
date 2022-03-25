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
import functools
import aiohttp
import logging
import traceback
import aiomysql
from discord import Webhook
from discord.ext import commands, tasks
import concurrent.futures
from tweepy.errors import NotFound
from tweepy.asynchronous import AsyncStream
from yagoo.scrapers.infoscraper import TwitterScrape
from yagoo.lib.dataUtils import botdb, dbTools

async def twtUpdater(pool: aiomysql.Pool):
    """
    Update Twitter user IDs.
    Has to be run every 15 minutes, and shouldn't be less as quotas renew every 15 minutes.
    More is fine.
    """
    write = False
    channelUpdate = []
    twitterUpdate = []
    
    db = await botdb.getDB(pool)
    channels = await botdb.getAllData("channels", ("id", "twitter"), db=db)
    scrape = await botdb.getAllData("scrape", ("id", "twitter"), keyDict="id", db=db)
    
    for channel in channels:
        try:
            if channel["twitter"] != scrape[channel["id"]]["twitter"]:
                twtID = await TwitterScrape.getUserID(scrape[channel["id"]]["twitter"])
                if twtID is not None:
                    channelUpdate.append((channel["id"], twtID))
                    twitterUpdate.append((twtID, channel["id"]))
                    write = True
        except (NotFound, KeyError) as e:
            logging.error(f"Twitter - Could not find user @{channel['twitter']}")
    
    if write:
        await botdb.addMultiData(channelUpdate, ("id", "twitter"), "channels", db)
        await botdb.addMultiData(twitterUpdate, ("twtID", "ytID"), "twitter", db)

async def twtSubscribe(bot, maintenance: bool):
    """
    Subscribes to tweets from Twitter IDs registered in `channels.json`.  
    Requires the async branch of `tweepy`.

    Arguments
    ---
    bot: An instance of `commands.Bot` from discord.py
    """
    twtUsers = []
    
    db = await botdb.getDB(bot.pool)
    customAcc = await botdb.getAllData("twitter", ("twtID", ), db=db)
    
    for account in customAcc:
        if account["twtID"]:
            if account["twtID"] != "None":
                twtUsers.append(account["twtID"])

    twtCred = await TwitterScrape.getCredentials()
    stream = twtPost(bot, bot.pool, twtUsers, maintenance, twtCred["apiKey"], twtCred["apiSecret"], twtCred["accessKey"], twtCred["accessSecret"])
    await stream.filter(follow=twtUsers)

class twtPost(AsyncStream):
    def __init__(self, bot, pool, twtUsers, maintenance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.pool = pool
        self.twtUsers = twtUsers
        self.maintenance = maintenance

    async def on_connect(self):
        logging.info("Twitter - Connected to Twitter Tweets stream!")

    async def on_status(self, tweet):
        # Twitter URL String: f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}"
        # Useful data points: User - tweet.user (dict), Tweet ID - tweet.id_str (string, no "_str" for actual number), Retweet - tweet.retweeted (boolean)
        # Retweeted Tweet - tweet.retweeted_status (Tweet Object), Quote Retweet - tweet.is_quote_status (boolean), Quoted Tweet - tweet.quoted_status (Tweet Object)
        # Like - tweet.favorited (boolean)
        # Wrap the url in "<>" to ensure no embeds are loaded (Which is probably not going to be used as we cannot send two embeds in one message)
        if tweet.user.id_str in self.twtUsers:
            db = await botdb.getDB(self.pool)
            channels = await botdb.getAllData("servers", ("server", "channel", "twitter", "custom"), keyDict="channel", db=db)

            if tweet.is_quote_status:
                twtString = f'@{tweet.user.screen_name} just retweeted @{tweet.quoted_status.user.screen_name}\'s tweet: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}\n'\
                            f'Quoted Tweet: https://twitter.com/{tweet.quoted_status.user.screen_name}/status/{tweet.quoted_status.id_str}'
            elif tweet.in_reply_to_screen_name is not None:
                twtString = f'@{tweet.user.screen_name} just replied to @{tweet.in_reply_to_screen_name}\'s tweet: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}\n'\
                            f'Replied Tweet: https://twitter.com/{tweet.in_reply_to_screen_name}/status/{tweet.in_reply_to_status_id_str}'
            elif "retweeted_status" in tweet._json:
                twtString = f'@{tweet.user.screen_name} just retweeted @{tweet.retweeted_status.user.screen_name}\'s tweet: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}'                
            elif tweet.favorited:
                twtString = f'@{tweet.user.screen_name} just liked @{tweet.retweeted_status.user.screen_name}\' tweet: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}'
            else:
                twtString = f'@{tweet.user.screen_name} tweeted just now: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}'

            async def postTweet(ptServer, ptChannel, db):
                try:
                    if not self.maintenance:
                        whurl = (await dbTools.serverGrab(self.bot, ptServer, ptChannel, ("url",), db))["url"]
                        async with aiohttp.ClientSession() as session:
                            webhook = Webhook.from_url(whurl, session=session)
                            await webhook.send(twtString, avatar_url=tweet.user.profile_image_url_https, username=tweet.user.name)
                    else:
                        print(f"Twitter Post on {ptChannel}:\n{twtString}\n")
                except Exception as e:
                    if "429 Too Many Requests" in str(e):
                        logging.warning(f"Too many requests for {ptChannel}! Sleeping for 10 seconds.")
                        await asyncio.sleep(10)
                    logging.error(f"Twitter - An error has occurred while publishing Twitter notification to {ptChannel}!", exc_info=True)

            queue = []
            for channel in channels:
                twitter = await botdb.listConvert(channels[channel]["twitter"])
                custom = await botdb.listConvert(channels[channel]["custom"])
                if twitter:
                    if tweet.user.id_str in twitter or tweet.user.screen_name in twitter:
                        queue.append(postTweet(channels[channel]["server"], channel, db))
                if custom:
                    if tweet.user.id_str in custom:
                        queue.append(postTweet(channels[channel]["server"], channel, db))
            await asyncio.gather(*queue)

    async def on_error(self, status):
        logging.error(f"Twitter - An error has occured!\nTweepy Error: {status}")

def updateWrapper(pool: aiomysql.Pool):
    asyncio.run(twtUpdater(pool))

class twtCycle(commands.Cog):
    def __init__(self, bot, maintenance):
        self.bot = bot
        self.subscribed = False
        self.maintenance = maintenance
    
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.maintenance:
            self.twtIDcheck.start()
        self.twtSubWrapper.start()

    def cog_unload(self):
        self.subscribed = False
        if not self.maintenance:
            self.twtIDcheck.cancel()
        self.twtSubWrapper.cancel()
    
    def botVar(self):
        return self.bot

    @tasks.loop(minutes=15.0)
    async def twtSubWrapper(self):
        try:
            if not self.subscribed:
                self.subscribed = True
            await twtSubscribe(self.bot, self.maintenance)
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)

    @tasks.loop(minutes=15.0)
    async def twtIDcheck(self):
        logging.info("Starting Twitter ID checks.")
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(pool, functools.partial(updateWrapper, self.bot.pool))
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)
        logging.info("Twitter ID checks done.")
