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

import json
import sys
import asyncio
import logging
import imgkit
import os
import shutil
import traceback
import platform
from mysql.connector.cursor import CursorBase
from yagoo.scrapers.infoscraper import FandomScrape, channelInfo, channelScrape
from yagoo.lib.dataUtils import botdb

logging.basicConfig(level=logging.INFO, filename='status.log', filemode='w', format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')

def channelscrape():
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)

    for channel in channels:
        chData = asyncio.run(channelInfo(channel))
        channels[channel] = {
            "name": chData["name"],
            "image": chData["image"],
            "milestone": chData["roundSubs"],
            "category": "Hololive"
        }
    with open("data/channels.json", "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4)

def msImage():
    options = {
        "enable-local-file-access": "",
        "encoding": "UTF-8",
        "quiet": ""
    }
    imgkit.from_file('milestone/milestone.html', 'milestone.png', options=options)

def subFormat(subnum):
    if subnum < 1000000:
        subtext = f'{int(subnum / 1000)}K Subscribers'
    else:
        if subnum == subnum - (subnum % 1000000):
            subtext = f'{int(subnum / 1000000)}M Subscribers'
        else:
            subtext = f'{subnum / 1000000}M Subscribers'
    return subtext

def bdayInsert():
    bdayData = {}
    months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    
    bdayData = {}
    for channel in channels:
        chInfo = asyncio.run(channelScrape(channel))
        x = 1
        try:
            for month in months:
                if month in chInfo["birthday"].lower():
                    for section in chInfo["birthday"].lower().replace(month, "").strip().split():
                        if len(section) <= 2:
                            chDay = section
                    if str(x) not in bdayData:
                        bdayData[str(x)] = {
                            chDay: [channel]
                        }
                        break
                    elif chDay not in bdayData[str(x)]:
                        bdayData[str(x)][chDay] = [channel]
                        break
                    else:
                        bdayData[str(x)][chDay].append(channel)
                        break
                x += 1
        except Exception as e:
            print(f"Couldn't get birthday for {chInfo['youtube']['name']}!")
            print("An error has occurred.")
            traceback.print_tb(e)
            continue
    
    with open("data/birthdays.json", "w") as f:
        json.dump(bdayData, f, indent=4, sort_keys=True)

def migrateData(version: str):
    if not os.path.exists("data_backup/"):
        os.mkdir("data_backup")
    if version == "1":
        shutil.copy("data/servers.json", "data_backup/servers.json")
        shutil.copy("data/channels.json", "data_backup/channels.json")
        
        with open("data/servers.json") as f:
            servers = json.load(f)
        
        with open("data/channels.json") as f:
            channels = json.load(f)
        
        newCh = {}

        print("Converting channel data...")
        for ytch in channels:
            chData = asyncio.run(channelInfo(channels[ytch]["channel"]))
            newCh[channels[ytch]["channel"]] = {
                "name": chData["name"],
                "image": chData["image"],
                "milestone": channels[ytch]["milestone"]
            }

        newServ = servers

        print("Converting server data...")
        for server in servers:
            for channel in servers[server]:
                livestream = []
                for sub in servers[server][channel]["subbed"]:
                    livestream.append(channels[sub]["channel"])
                newServ[server][channel]["livestream"] = livestream
                newNot = {}
                for chNot in servers[server][channel]["notified"]:
                    chLink = channels[chNot]["channel"]
                    newNot[chLink] = servers[server][channel]["notified"][chNot]
                newServ[server][channel]["notified"] = newNot
                newServ[server][channel]["milestone"] = livestream
                newServ[server][channel].pop("subbed", None)
        
        with open("data/servers.json", "w") as f:
            json.dump(servers, f, indent=4)
        
        with open("data/channels.json", "w", encoding="utf-8") as f:
            json.dump(newCh, f, indent=4)
    elif version == "2":
        shutil.copy("data/channels.json", "data_backup/channels.json")

        with open("data/channels.json") as f:
            channels = json.load(f)
        
        print("Converting channel data...")
        for channel in channels:
            channels[channel]["category"] = "Hololive"
        
        with open("data/channels.json", "w", encoding="utf-8") as f:
            json.dump(channels, f, indent=4)
    elif version == "3":
        shutil.copy("data/channels.json", "data_backup/channels.json")

        with open("data/channels.json") as f:
            channels = json.load(f)
        
        print("Converting channel data...")
        for channel in channels:
            channels[channel]["category"] = asyncio.run(FandomScrape.getAffiliate(channels[channel]["name"]))
        
        with open("data/channels.json", "w", encoding="utf-8") as f:
            json.dump(channels, f, indent=4)
    elif version == "4":
        if os.path.exists("data_backup"):
            shutil.copy("data/servers.json", "data_backup/servers.json")
        else:
            os.mkdir("data_backup")
            shutil.copy("data/servers.json", "data_backup/servers.json")
        with open("data/servers.json") as f:
            servers = json.load(f)
        
        for server in servers:
            for channel in servers[server]:
                if "livestream" in servers[server][channel]:
                    servers[server][channel]["premiere"] = servers[server][channel]["livestream"]
        
        with open("data/servers.json", "w") as f:
            json.dump(servers, f, indent=4)
    elif version == "5":
        asyncio.run(sqlMigrate())
    elif version == "6":
        asyncio.run(addPrefix())

async def sqlMigrate():
    dataFiles = ["channels", "scrape", "servers", "twitter"]
    
    db = await botdb.getDB()
    cursor: CursorBase = db.cursor()
    
    for file in dataFiles:
        found = False
        index = 0
        cursor.execute("SHOW tables")
        for x in cursor.fetchall():
            if file in x:
                found = True

        with open(f"data/{file}.json") as f:
            fileData = json.load(f)
        
        multiData = []
        seperator = "|yb|"
        if file == "channels":
            dataTypes = ("id", "name", "image", "milestone", "category", "twitter")
            
            if not found:
                print("Creating table 'channels' as it does not exist!")
                cursor.execute("CREATE TABLE channels (id VARCHAR(25), name VARCHAR(500), image VARCHAR(200), milestone INT, category VARCHAR(100), twitter VARCHAR(30))")
            
            for channel in fileData:
                chInfo = fileData[channel]
                if "twitter" in chInfo:
                    multiData.append((channel, chInfo["name"], chInfo["image"], chInfo["milestone"], chInfo["category"], chInfo["twitter"]))
                else:
                    multiData.append((channel, chInfo["name"], chInfo["image"], chInfo["milestone"], chInfo["category"], None))
        elif file == "scrape":
            dataTypes = ("id", "name", "image", "realSubs", "roundSubs", "premieres", "streams", "banner", "mbanner", "twitter")
            
            if not found:
                print("Creating table 'scrape' as it does not exist!")
                cursor.execute("CREATE TABLE scrape (id VARCHAR(25), name VARCHAR(500), image VARCHAR(200), realSubs INT, roundSubs INT, premieres TEXT(10000), streams TEXT(10000), banner VARCHAR(200), mbanner VARCHAR(200), twitter VARCHAR(30))")
            
            for channel in fileData:
                chInfo = fileData[channel]
                if "twitter" in chInfo:
                    multiData.append((channel, chInfo["name"], chInfo["image"], chInfo["realSubs"], chInfo["roundSubs"], json.dumps(chInfo["premieres"]), "{}", chInfo["banner"], chInfo["mbanner"], chInfo["twitter"]))
                else:
                    multiData.append((channel, chInfo["name"], chInfo["image"], chInfo["realSubs"], chInfo["roundSubs"], json.dumps(chInfo["premieres"]), "{}", chInfo["banner"], chInfo["mbanner"], None))
        elif file == "servers":
            index = 1
            dataTypes = ("server", "channel", "url", "notified", "subDefault", "livestream", "milestone", "premiere", "twitter", "custom")
            
            if not found:
                print("Creating table 'servers' as it does not exist!")
                cursor.execute("CREATE TABLE servers (server TEXT(20), channel TEXT(20), url TEXT(120), notified TEXT(30000), subDefault TEXT(200), livestream TEXT(5000), milestone TEXT(5000), premiere TEXT(5000), twitter TEXT(5000), custom TEXT(5000))")
            
            multiData = []
            for server in fileData:
                serverData = []
                for channel in fileData[server]:
                    chDict = fileData[server][channel]
                    
                    if "url" in chDict:
                        whurl = chDict["url"]
                    else:
                        whurl = ""
                    
                    if "notified" in chDict:
                        notified = json.dumps(chDict["notified"])
                    else:
                        notified = ""
                    
                    if "subDefault" in chDict:
                        subDefault = seperator.join(chDict["subDefault"])
                    else:
                        subDefault = ""
                        
                    if "livestream" in chDict:
                        livestream = seperator.join(chDict["livestream"])
                    else:
                        livestream = ""
                        
                    if "milestone" in chDict:
                        milestone = seperator.join(chDict["milestone"])
                    else:
                        milestone = ""
                        
                    if "premiere" in chDict:
                        premiere = seperator.join(chDict["premiere"])
                    else:
                        premiere = ""
                        
                    if "twitter" in chDict:
                        twitter = seperator.join(chDict["twitter"])
                    else:
                        twitter = ""
                    
                    if "custom" in chDict:
                        custom = seperator.join(chDict["custom"])
                    else:
                        custom = ""
                    
                    serverData.append((server, channel, whurl, notified, subDefault, livestream, milestone, premiere, twitter, custom))
                multiData += serverData
        elif file == "twitter":
            dataTypes = ("twtID", "ytID", "custom", "name", "screenName")
            
            if not found:
                print("Creating table 'twitter' as it does not exist!")
                cursor.execute("CREATE TABLE twitter (twtID VARCHAR(30), ytID VARCHAR(30), custom INT, name VARCHAR(500), screenName VARCHAR(200))")
            
            for accID in fileData:
                if accID != "custom":
                    multiData.append((accID, fileData[accID], 0, None, None))
                else:
                    for custID in fileData["custom"]:
                        multiData.append((custID, None, 1, fileData["custom"][custID]["name"], fileData["custom"][custID]["screen_name"]))
        
        await botdb.addMultiData(multiData, dataTypes, file, db, index)
        db.commit()

    if os.path.exists("data_old"):
        shutil.copy("data/servers.json", "data_backup/servers.json")
    else:
        os.mkdir("data_old")
        shutil.copy("data/servers.json", "data_backup/servers.json")

async def addPrefix():
    db = await botdb.getDB()
    cursor: CursorBase = db.cursor()
    cursor.execute("CREATE TABLE prefixes (server VARCHAR(30), prefix VARCHAR(30))")

async def affUpdate():
    tasks = []
    with open("data/channels.json") as f:
        channels = json.load(f)

    async def channelUpdate(channel):
        chInfo = await channelInfo(channel)
        return {
            "channel": channel,
            "affiliate": await FandomScrape.getAffiliate(chInfo["name"])
        }

    for channel in channels:
        tasks.append(channelUpdate(channel))

    liveCh = await asyncio.gather(*tasks)

    for channel in liveCh:
        channels[channel["channel"]]["category"] = channel["affiliate"]

    with open("data/channels.json", "w") as f:
        json.dump(channels, f, indent=4)

async def msUpdate():
    db = await botdb.getDB()
    channels = await botdb.getAllData("channels", ("id", "milestone"), db=db)
    scrape = await botdb.getAllData("scrape", ("id", "roundSubs"), keyDict="id", db=db)
    
    async def update(channel: tuple, scrape: dict):
        if channel["milestone"] < scrape["roundSubs"]:
            return {
                "id": channel["id"],
                "milestone": scrape["roundSubs"]
            }
        return None
    
    queue = []
    for channel in channels:
        try:
            queue.append(update(channel, scrape[channel["id"]]))
        except Exception as e:
            print(f"Channel \"{channel['id']}\" needs manual updating!")
    
    updateList = []
    write = False
    results = await asyncio.gather(*queue)
    for result in results:
        if result:
            updateList.append((result["id"], result["milestone"]))
            write = True
    
    if write:
        await botdb.addMultiData(updateList, ("id", "milestone"), "channels", db)

# To be used in programs only, not the CLI
async def debugFile(output, filetype, filename):
    print("Writing to file...")
    with open(f'test/{filename}.{filetype}', "w", encoding="utf-8") as f:
        if filetype == "json":
            json.dump(output, f, indent=4)
        else:
            f.write(output)

if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    if sys.argv[1] == "migrate":
        if len(sys.argv) == 3:
            print("Migrating data files to new format...")
            migrateData(sys.argv[2])
            print("Data files are now converted. Backups are in the 'data_backup' folder.")
        else:
            print("Enter a data migration version. (Versions available: 1, 2)")
    elif sys.argv[1] == "scrape":
        print("Scraping channels...")
        channelscrape()
        print("Done.")
    elif sys.argv[1] == "image":
        print("Generating milestone image...")
        msImage()
        print("Done.")
    elif sys.argv[1] == "sub":
        print("Formatting subscribers count...")
        subFormat(int(sys.argv[2]))
        print("Done.")
    elif sys.argv[1] == "milestone":
        print("Updating milestones....")
        asyncio.run(msUpdate())
        print("Done.")
    elif sys.argv[1] == "bday":
        print("Getting member birthdays...")
        bdayInsert()
        print("Done.")
    elif sys.argv[1] == "affiliate":
        print("Updating channel affiliates...")
        asyncio.run(affUpdate())
        print("Done.")
    else:
        print("No valid command was entered!\nValid commands are scrape, clean, image and sub.")
