import json
import yaml
import asyncio
import aiohttp
import concurrent.futures
import rpyc
import traceback
from bs4 import BeautifulSoup
from dbStandalone import botdb

with open("settings.yaml") as f:
    settings = yaml.load(f, Loader=yaml.SafeLoader)

async def uplThumbnail(channelID, videoID, live=True):
    extServer = rpyc.connect(settings["thumbnailIP"], int(settings["thumbnailPort"]))
    asyncUpl = rpyc.async_(extServer.root.thumbGrab)
    uplSuccess = False

    for x in range(3):
        if live:
            upload = asyncUpl(channelID, f'https://img.youtube.com/vi/{videoID}/maxresdefault_live.jpg')
        else:
            upload = asyncUpl(channelID, f'https://img.youtube.com/vi/{videoID}/maxresdefault.jpg')
        uplSuccess = False

        while True:
            if upload.ready and not upload.error:
                uplSuccess = True
                break
            elif upload.error:
                break

            await asyncio.sleep(0.5)

        if not uplSuccess or "yagoo.ezz.moe" not in upload.value:
            print("Stream - Couldn't upload thumbnail!")
            print(upload.value)
            return None
        return upload.value

def round_down(num, divisor):
    return num - (num%divisor)

async def formatMilestone(msCount):
    if "M" in msCount:
        cSubsA = int(float(msCount.replace("M subscribers", "")) * 1000000)
        cSubsR = round_down(cSubsA, 500000)
    elif "K" in msCount:
        cSubsA = int(float(msCount.replace("K subscribers", "")) * 1000)
        cSubsR = round_down(cSubsA, 100000)
    else:
        cSubsA = int(float(msCount.replace(" subscribers", "")))
        cSubsR = 0
    
    return cSubsA, cSubsR

async def scrape(channel: str):
    """
    Grabs the stream data of the channel.
    """
    streams = {
        "premieres": {},
        "live": {}
    }
    result = {}
    error = None
    exists = True
    
    for x in range(3):
        try:
            consent = {'CONSENT': 'YES+cb.20210328-17-p0.en+FX+162'}
            async with aiohttp.ClientSession(cookies=consent) as session:
                if settings["proxy"]:
                    proxy = f"http://{settings['proxyIP']}:{settings['proxyPort']}"
                    proxyauth = aiohttp.BasicAuth(settings["proxyUsername"], settings["proxyPassword"])
                else:
                    proxy = None
                    proxyauth = None
                async with session.get(f'https://www.youtube.com/channel/{channel}/videos?hl=en-US', proxy=proxy, proxy_auth=proxyauth) as r:
                    soup = BeautifulSoup(await r.text(), "lxml")
                    scripts = soup.find_all("script")
                    for script in scripts:
                        if ("var ytInitialData" in script.getText()) or ('window["ytInitialData"]' in script.getText()):
                            ytdata = json.loads(script.getText().replace(';', '').replace('var ytInitialData = ', '').replace('window["ytInitialData"]', ''))
                            if "messageRenderer" in ytdata["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][1]["tabRenderer"]["content"] \
                                                          ["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"][0]:
                                exists = False
                            if exists:
                                videos = ytdata["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][1]["tabRenderer"]["content"]["sectionListRenderer"] \
                                               ["contents"][0]["itemSectionRenderer"]["contents"][0]["gridRenderer"]["items"]
                                streams = await streamParse(videos, channel)

                            cSubsA, cSubsR = await formatMilestone(ytdata["header"]["c4TabbedHeaderRenderer"]["subscriberCountText"]["simpleText"])
                            result = {
                                "id": channel,
                                "name": ytdata["metadata"]["channelMetadataRenderer"]["title"],
                                "image": ytdata["metadata"]["channelMetadataRenderer"]["avatar"]["thumbnails"][0]["url"],
                                "realSubs": cSubsA,
                                "roundSubs": cSubsR,
                                "success": True,
                                "streams": streams
                            }
                            
                            try:
                                result["banner"] = ytdata["header"]["c4TabbedHeaderRenderer"]["banner"]["thumbnails"][3]["url"]
                            except Exception as e:
                                result["banner"] = None

                            try:
                                result["mbanner"] = ytdata["header"]["c4TabbedHeaderRenderer"]["banner"]["thumbnails"][1]["url"]
                            except Exception as e:
                                result["mbanner"] = None

                            if "headerLinks" in ytdata["header"]["c4TabbedHeaderRenderer"]:
                                found = False
                                for link in ytdata["header"]["c4TabbedHeaderRenderer"]["headerLinks"]["channelHeaderLinksRenderer"]["primaryLinks"]:
                                    if "twitter.com" in link["navigationEndpoint"]["urlEndpoint"]["url"] and not found:
                                        result["twitter"] = link["navigationEndpoint"]["urlEndpoint"]["url"].split("&q=")[-1].split("%2F")[-1].split("%3F")[0]
                                        found = True
                                if not found and "secondaryLinks" in ytdata["header"]["c4TabbedHeaderRenderer"]["headerLinks"]["channelHeaderLinksRenderer"]:
                                    for link in ytdata["header"]["c4TabbedHeaderRenderer"]["headerLinks"]["channelHeaderLinksRenderer"]["secondaryLinks"]:
                                        if "twitter.com" in link["navigationEndpoint"]["urlEndpoint"]["url"] and not found:
                                            result["twitter"] = link["navigationEndpoint"]["urlEndpoint"]["url"].split("&q=")[-1].split("%2F")[-1].split("%3F")[0]
            await asyncio.sleep(5)
            return result
        except Exception as e:
            error = e
            await asyncio.sleep(5)
            continue
    print(f"An error has occurred while scraping for channel {channel}!")
    traceback.print_exception(type(error), error, error.__traceback__)
    return None

async def streamParse(videos: list, channel: str):
    result = {
        "premieres": {},
        "live": {}
    }
    live = False
    
    for video in videos:
        if "gridVideoRenderer" in video:
            label = video["gridVideoRenderer"]["thumbnailOverlays"][0]["thumbnailOverlayTimeStatusRenderer"]["text"]["accessibility"]\
                         ["accessibilityData"]["label"]
            if not label[0].isdigit():
                title = ""
                status = ""
                upcoming = None
                if label == "LIVE":
                    live = True
                if label == "Shorts":
                    live = False
                for part in video["gridVideoRenderer"]["title"]["runs"]:
                    title += part["text"]
                if "simpleText" in video["gridVideoRenderer"]["viewCountText"]:
                    status = video["gridVideoRenderer"]["viewCountText"]["simpleText"]
                else:
                    for part in video["gridVideoRenderer"]["viewCountText"]["runs"]:
                        status += part["text"]
                if "upcomingEventData" in video["gridVideoRenderer"]:
                    upcoming = video["gridVideoRenderer"]["upcomingEventData"]["startTime"]
                thumbnail = await uplThumbnail(channel, video["gridVideoRenderer"]["videoId"], live)
                if label == "PREMIERE":
                    result["premieres"][video["gridVideoRenderer"]["videoId"]] = {
                        "title": title,
                        "upcoming": upcoming,
                        "status": status,
                        "thumbnail": thumbnail
                    }
                elif live and "waiting" not in status:
                    result["live"][video["gridVideoRenderer"]["videoId"]] = {
                        "title": title,
                        "status": status,
                        "thumbnail": thumbnail
                    }
    
    return result

async def queue():
    queue = []
    upload = []
    uploadTypes = ("id", "name", "image", "realSubs", "roundSubs", "premieres", "streams", "banner", "mbanner", "twitter")
    
    db = await botdb.getDB()
    channels = await botdb.getAllData("channels", ("id",), db=db)
    
    for channel in channels:
        queue.append(scrape(channel["id"]))
    results = await asyncio.gather(*queue)
    
    for result in results:
        if result:
            if "twitter" in result:
                upload.append((result["id"], result["name"], result["image"], result["realSubs"], result["roundSubs"], json.dumps(result["streams"]["premieres"]), json.dumps(result["streams"]["live"]), result["banner"], result["mbanner"], result["twitter"]))
            else:
                upload.append((result["id"], result["name"], result["image"], result["realSubs"], result["roundSubs"], json.dumps(result["streams"]["premieres"]), json.dumps(result["streams"]["live"]), result["banner"], result["mbanner"], None))
    
    await botdb.addMultiData(upload, uploadTypes, "scrape", db)

def scrapeWrapper():
    asyncio.run(queue())

async def init():
    print("Starting scraper...")
    while True:
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                loop = asyncio.get_running_loop()
                print("Scraper is now scraping channels...")
                await loop.run_in_executor(pool, scrapeWrapper)
        except Exception as e:
            print("An error has occurred!")
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            print("Channel scrape done.")
        await asyncio.sleep(1.5*60)

if __name__ == "__main__":
    asyncio.run(init())
    #print(asyncio.run(scrape("UCa_UMppcMsHIzb5LDx1u9zQ")))
    #asyncio.run(test())
