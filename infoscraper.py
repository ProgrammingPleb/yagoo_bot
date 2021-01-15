import json, aiohttp, asyncio, re, sys, logging
from bs4 import BeautifulSoup
from typing import Union

def round_down(num, divisor):
    return num - (num%divisor)

async def streamInfo(channelId: Union[str, int]):
    output = None

    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://www.youtube.com/channel/{channelId}/live?hl=en-US') as r:
            soup = BeautifulSoup(await r.text(), "html5lib")
            scripts = soup.find_all("script")
            for script in scripts:
                if ("var ytInitialData" in script.getText()) or ('window["ytInitialData"]' in script.getText()):
                    ytdata = json.loads(script.getText().replace(';', '').replace('var ytInitialData = ', '').replace('window["ytInitialData"]', ''))
                    isVideo = False
                    for cat in ytdata:
                        if cat == "playerOverlays":
                            isVideo = True
                    if isVideo:
                        morevInfo = ytdata["contents"]["twoColumnWatchNextResults"]["results"]["results"]["contents"][0]["videoPrimaryInfoRenderer"]
                        if "viewCount" in morevInfo:
                            videoInfo = morevInfo["viewCount"]["videoViewCountRenderer"]
                            if videoInfo["isLive"] and ("watching now" in videoInfo["viewCount"]["runs"][0]["text"]):
                                title = ""
                                if len(morevInfo["title"]["runs"]) > 1:
                                    for subrun in morevInfo["title"]["runs"]:
                                        title += subrun["text"]
                                else:
                                    title = morevInfo["title"]["runs"][0]["text"]
                                output = {
                                    "isLive": True,
                                    "videoId": morevInfo["updatedMetadataEndpoint"]["updatedMetadataEndpoint"]["videoId"],
                                    "videoTitle": title,
                                    "timeText": morevInfo["dateText"]["simpleText"].replace('Started streaming ', '')
                                }
                            else:
                                output = {
                                    "isLive": False
                                }
    if not output:
        output = {
            "isLive": False
        }
    return output

async def channelInfo(channelId: Union[str, int]):
    channelData = None
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://www.youtube.com/channel/{channelId}?hl=en-US') as r:
            soup = BeautifulSoup(await r.text(), "html5lib")
            scripts = soup.find_all("script")
            for script in scripts:
                if ("var ytInitialData" in script.getText()) or ('window["ytInitialData"]' in script.getText()):
                    ytdata = json.loads(script.getText().replace(';', '').replace('var ytInitialData = ', '').replace('window["ytInitialData"]', ''))

                    cSubsText = ytdata["header"]["c4TabbedHeaderRenderer"]["subscriberCountText"]["simpleText"]

                    if "M" in cSubsText:
                        cSubsA = int(float(cSubsText.replace("M subscribers", "")) * 1000000)
                        cSubsR = round_down(cSubsA, 500000)
                    elif "K" in cSubsText:
                        cSubsA = int(float(cSubsText.replace("K subscribers", "")) * 1000)
                        cSubsR = round_down(cSubsA, 100000)
                    else:
                        cSubsA = None
                        cSubsR = None

                    channelData = {
                        "name": ytdata["metadata"]["channelMetadataRenderer"]["title"],
                        "formattedName": re.split(r'([a-zA-Z\xC0-\xFF]+)', ytdata["metadata"]["channelMetadataRenderer"]["title"]),
                        "image": ytdata["metadata"]["channelMetadataRenderer"]["avatar"]["thumbnails"][0]["url"],
                        "banner": ytdata["header"]["c4TabbedHeaderRenderer"]["banner"]["thumbnails"][3]["url"],
                        "mbanner": ytdata["header"]["c4TabbedHeaderRenderer"]["banner"]["thumbnails"][1]["url"],
                        "realSubs": cSubsA,
                        "roundSubs": cSubsR,
                        "success": True
                    }
    
    if channelData == None:
        channelData = {
            "success": False
        }
    return channelData

async def channelScrape(query: str):

    if "/channel/" in query:
        query = query.split("/")[-1]
    
    chInfo = await channelInfo(query)
    if chInfo["success"] == False:
        return {
            "success": False
        }
    else:
        chNSplit = chInfo["name"].split()
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f'https://virtualyoutuber.fandom.com/api.php?action=opensearch&format=json&search={chInfo["name"]}') as r:
                """soup = BeautifulSoup(await r.text(), "html5lib")
                sArticles = soup.find("ul", {"class": "unified-search__results"}).find_all("article")
                chLink = None
                for article in sArticles:
                    for name in chNSplit:
                        if name in article.text:
                            chLink = article.find("a")["href"]"""
                resp = await r.json()
                chLink = None
                x = 0
                for title in resp[1]:
                    for name in chNSplit:
                        if name in title:
                            chLink = title
                    x += 1
                if chLink == None:
                    logging.debug("Not found! Returning to first entry.")
                    chLink = resp[1][0]
            async with session.get(f'https://virtualyoutuber.fandom.com/api.php?action=parse&format=json&page={chLink.split("/")[0]}') as r:
                resp = await r.json()
                for prop in resp["parse"]["properties"]:
                    if prop["name"] == "infoboxes":
                        infobox = prop["*"]
                        break
                    x += 1
                infobox = json.loads(infobox)
                dataSource = infobox[0]["data"][4]["data"]["value"]
        
        result = {
            "success": True,
            "youtube": chInfo
        }

        infoGrab = {
            "1": {
                "dict": "gender",
                "source": "gender"
            },
            "2": {
                "dict": "height",
                "source": "height"
            },
            "3": {
                "dict": "age",
                "source": "age"
            },
            "4": {
                "dict": "birthday",
                "source": "birthday"
            }
        }

        for entry in infoGrab:
            infoPresent = False
            for data in dataSource:
                if data["type"] == "data":
                    if data["data"]["source"] == infoGrab[entry]["source"]:
                        result[infoGrab[entry]["dict"]] = re.sub('\[\d+\]', '', data["data"]["value"].replace('\n', ''))
                        infoPresent = True
            if not infoPresent:
                result[infoGrab[entry]["dict"]] = None

        return result

def sInfoAdapter(id):
    cData = asyncio.run(channelScrape(id))
    print(cData)

if __name__ == "__main__":
    sInfoAdapter(sys.argv[1])
