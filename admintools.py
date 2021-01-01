import json, requests, sys, asyncio, logging, imgkit
from imgkit.api import config
from bs4 import BeautifulSoup
from infoscraper import channelInfo

logging.basicConfig(level=logging.INFO, filename='status.log', filemode='w', format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')

def channelscrape():
    with open("channels.json", encoding="utf-8") as f:
        channels = json.load(f)

    for channel in channels:
        if channels[channel]["channel"] != "":
            with requests.get(f'https://www.youtube.com/channel/{channels[channel]["channel"]}') as r:
                soup = BeautifulSoup(r.text, "lxml")
                scripts = soup.find_all("script")
                for script in scripts:
                    if "var ytInitialData" in script.getText():
                        ytdata = json.loads(script.getText().replace(';', '').replace('var ytInitialData = ', ''))
                        for x in range(2):
                            try:
                                ytinfo = asyncio.run(channelInfo(channels[channel]["channel"]))
                            except:
                                if x == 2:
                                    break
                        print(ytinfo)
                        channels[channel]["milestone"] = ytinfo["roundSubs"]
                        cinfo = ytdata["metadata"]["channelMetadataRenderer"]
                        print(cinfo["title"])
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4)

def channelClean():
    with open("channels.json", encoding="utf-8") as f:
        channels = json.load(f)
    
    for channel in channels:
        channels[channel].pop("name", None)
        channels[channel].pop("image", None)
        channels[channel].pop("subbed", None)
    
    with open("channels.json", "w", encoding="utf-8") as f:
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
    print(subtext)

if __name__ == "__main__":
    if sys.argv[1] == "scrape":
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
