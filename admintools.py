import json, requests, sys, asyncio, logging, imgkit, os, shutil, yaml
from imgkit.api import config
from bs4 import BeautifulSoup
from infoscraper import channelInfo, channelScrape

logging.basicConfig(level=logging.INFO, filename='status.log', filemode='w', format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')

def channelscrape():
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)

    for channel in channels:
        ytinfo = asyncio.run(channelInfo(channels[channel]["channel"]))
        channels[channel]["milestone"] = ytinfo["roundSubs"]
    with open("data/channels.json", "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4)

def channelClean():
    with open("data/channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    
    for channel in channels:
        channels[channel].pop("name", None)
        channels[channel].pop("image", None)
        channels[channel].pop("subbed", None)
    
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
        chInfo = asyncio.run(channelScrape(channels[channel]["channel"]))
        x = 1
        try:
            for month in months:
                if month in chInfo["birthday"].lower():
                    for section in chInfo["birthday"].lower().replace(month, "").strip().split():
                        if len(section) <= 2:
                            chDay = section
                    if str(x) not in bdayData:
                        bdayData[str(x)] = {
                            chDay: [channels[channel]["channel"]]
                        }
                        break
                    elif chDay not in bdayData[str(x)]:
                        bdayData[str(x)][chDay] = [channels[channel]["channel"]]
                        break
                    else:
                        bdayData[str(x)][chDay].append(channels[channel]["channel"])
                        break
                x += 1
        except:
            print(f"Couldn't get birthday for {chInfo['youtube']['name']}!")
            continue
    
    with open("data/birthdays.json", "w") as f:
        json.dump(bdayData, f, indent=4, sort_keys=True)

def initBot():
    if not os.path.exists("data"):
        print("Creating data directory...")
        os.mkdir("data")
    if not os.path.exists("data/servers.json"):
        shutil.copy("setup/blank.json", "data/servers.json")
    if not os.path.exists("data/bot.json"):
        shutil.copy("setup/blank.json", "data/bot.json")
    if not os.path.exists("data/channels.json"):
        shutil.copy("setup/channels.json", "data/channels.json")
    if not os.path.exists("data/settings.yaml"):
        shutil.copy("setup/settings.yaml", "data/settings.yaml")
    with open("data/settings.yaml") as f:
        settings = yaml.load(f, Loader=yaml.FullLoader)
    if settings["token"] != None:
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

def migrateData():
    if not os.path.exists("data_backup/"):
        os.mkdir("data_backup")
    if not os.path.exists("data/servers.json"):
        shutil.copy("data/servers.json", "data_backup/servers.json")
    if not os.path.exists("data/channels.json"):
        shutil.copy("data/channels.json", "data_backup/channels.json")
    
    with open("data/servers.json") as f:
        servers = json.load(f)
    
    with open("data/channels.json") as f:
        channels = json.load(f)
    
    newCh = {}

    print("Converting channel data...")
    for ytch in channels:
        chData = asyncio.run(channelInfo(channels[ytch]["channel"]))
        newCh[ytch] = {
            "name": chData["name"],
            "image": chData["image"],
            "milestone": channels[ytch]["milestone"]
        }

    print("Converting server data...")
    for server in servers:
        for channel in servers[server]:
            for sub in servers[server][channel]["subbed"]:
                if "livestream" not in servers[server][channel]:
                    servers[server][channel]["livestream"] = [channels[sub]["channel"]]
                else:
                    servers[server][channel]["livestream"].append(channels[sub]["channel"])
            servers[server][channel]["milestone"] = servers[server][channel]["livestream"]
            servers[server][channel].pop("subbed", None)
    
    with open("data/servers.json", "w") as f:
        json.dump(servers, f, indent=4)
    
    with open("data/channels.json", "w", encoding="utf-8") as f:
        json.dump(newCh, f, indent=4)

# To be used in programs only, not the CLI
async def debugFile(output, type, filename):
    print("Writing to file...")
    with open(f'test/{filename}.{type}', "w", encoding="utf-8") as f:
        if type == "json":
            json.dump(output, f, indent=4)
        else:
            f.write(output)

if __name__ == "__main__":
    if sys.argv[1] == "init":
        print("Prepping initial data for bot...")
        initBot()
        print("Bot can now be started by launching the bot.py file.")
    elif sys.argv[1] == "migrate":
        print("Migrating data files to new format...")
        migrateData()
        print("Data files are now converted. Backups are in the 'data_backup' folder.")
    elif sys.argv[1] == "scrape":
        print("Scraping channels...")
        channelscrape()
        print("Done.")
    elif sys.argv[1] == "clean":
        print("Cleaning unused keys...")
        channelClean()
        print("Done.")
    elif sys.argv[1] == "image":
        print("Generating milestone image...")
        msImage()
        print("Done.")
    elif sys.argv[1] == "sub":
        print("Formatting subscribers count...")
        subFormat(int(sys.argv[2]))
        print("Done.")
    elif sys.argv[1] == "bday":
        print("Getting member birthdays...")
        bdayInsert()
        print("Done.")
    else:
        print("No valid command was entered!\nValid commands are scrape, clean, image and sub.")
