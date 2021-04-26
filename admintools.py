import json
import sys
import asyncio
import logging
import imgkit
import os
import shutil
import yaml
import traceback
import platform
from bs4 import BeautifulSoup
from ext.infoscraper import FandomScrape, channelInfo, channelScrape

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

def initBot():
    if not os.path.exists("data"):
        print("Creating data directory...")
        os.mkdir("data")
    if not os.path.exists("data"):
        print("Creating generated milestones directory...")
        os.mkdir("milestone/generated")
    if not os.path.exists("data/servers.json"):
        shutil.copy("setup/blank.json", "data/servers.json")
    if not os.path.exists("data/bot.json"):
        shutil.copy("setup/blank.json", "data/bot.json")
    if not os.path.exists("data/channels.json"):
        shutil.copy("setup/channels.json", "data/channels.json")
    if not os.path.exists("data/settings.yaml"):
        shutil.copy("setup/settings.yaml", "data/settings.yaml")
    with open("data/settings.yaml") as f:
        settings = yaml.load(f, Loader=yaml.SafeLoader)
    if settings["token"] is not None:
        print("This bot is already setup!")
        return
    print("To get a bot token, go to https://discord.com/developers/ and make a new application.\n"
          "Go to the application that was made, click on 'Bot' on the sidebar, and click on 'Add Bot'\n"
          "Below 'Token' is a 'Copy' button, click on it and paste it below.")
    settings["token"] = input("Bot Token: ")
    print("Collecting channel data...")
    channelscrape()
    print("Generating birthday file...")
    bdayInsert()
    print("Saving settings...")
    with open("data/settings.yaml", "w") as f:
        yaml.dump(settings, f)

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
    if version == "2":
        shutil.copy("data/channels.json", "data_backup/channels.json")

        with open("data/channels.json") as f:
            channels = json.load(f)
        
        print("Converting channel data...")
        for channel in channels:
            channels[channel]["category"] = "Hololive"
        
        with open("data/channels.json", "w", encoding="utf-8") as f:
            json.dump(channels, f, indent=4)
    if version == "3":
        shutil.copy("data/channels.json", "data_backup/channels.json")

        with open("data/channels.json") as f:
            channels = json.load(f)
        
        print("Converting channel data...")
        for channel in channels:
            channels[channel]["category"] = asyncio.run(FandomScrape.getAffiliate(channels[channel]["name"]))
        
        with open("data/channels.json", "w", encoding="utf-8") as f:
            json.dump(channels, f, indent=4)
    if version == "4":
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
    async def chMsGet(channel):
        x = 1
        try:
            chInfo = await channelInfo(channel)
            return {
                "channel": channel,
                "subs": chInfo["roundSubs"]
            }
        except Exception as e:
            if x != 3:
                x += 1
            else:
                return

    with open("data/channels.json") as f:
        channels = json.load(f)

    chList = []
    for channel in channels:
        chList.append(chMsGet(channel))
    allCh = await asyncio.gather(*chList)

    for channel in allCh:
        channels[channel["channel"]]["milestone"] = channel["subs"]

    with open("data/channels.json", "w") as f:
        json.dump(channels, f, indent=4)

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
    
    if sys.argv[1] == "init":
        print("Prepping initial data for bot...")
        initBot()
        print("Bot can now be started by launching the bot.py file.")
    elif sys.argv[1] == "migrate":
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
