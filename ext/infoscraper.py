import json
import aiohttp
import asyncio
import re
import sys
import logging
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
                    logging.debug("Got ytInitialData!")
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
    
    if channelData is None:
        channelData = {
            "success": False
        }
    return channelData

class FandomScrape():

    async def searchChannel(chName, silent = False):
        chNSplit = chName.split()

        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://virtualyoutuber.fandom.com/api.php?action=opensearch&format=json&search={chName}') as r:
                resp = await r.json()
                chLink = None
                nameList = []
                x = 0
                for title in resp[1]:
                    for name in chNSplit:
                        if name.lower() in title.lower() and len(title.split("/")) < 2:
                            chLink = {
                                "status": "Success",
                                "name": title,
                                "results": nameList
                            }
                    if len(title.split("/")) < 2:
                        nameList.append(title)
                    x += 1
                if chLink is None:
                    if silent:
                        logging.debug("Not found! Returning to first entry.")
                        chLink = {
                                "status": "Success",
                                "name": resp[1][0]
                            }
                    else:
                        chLink = {
                            "status": "Cannot Match",
                            "results": nameList
                        }
        
        return chLink
    
    async def getChannel(chLink, dataKey = "infobox", scope = 4):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://virtualyoutuber.fandom.com/api.php?action=parse&format=json&page={chLink.split("/")[0]}') as r:
                resp = await r.json()
                if dataKey == "text":
                    dataSource = (resp["parse"]["text"]["*"])
                elif dataKey == "infobox":
                    for prop in resp["parse"]["properties"]:
                        if prop["name"] == "infoboxes":
                            infobox = prop["*"]
                            break
                    infobox = json.loads(infobox)
                    dataSource = infobox[0]["data"][scope]["data"]["value"]
                elif dataKey == "full":
                    dataSource = resp
                else:
                    dataSource = None
        
        return dataSource
    
    async def parseChannelText(dataText, scrapeList: list = None):
        if scrapeList is None:
            scrapeList = ["Profile", "Personality"]
        
        outputData = []

        soup = BeautifulSoup(dataText, "html5lib")
        for webObj in scrapeList:
            try:
                header = soup.find("span", {"id": webObj}).parent
                headData = header.find_next_sibling(['p', 'h2'])
                if headData.name == "h2":
                    raise AttributeError
                headData = re.sub('\[\d+\]', '', headData.get_text().strip())
            except AttributeError:
                headData = None
            outputData.append({
                "name": webObj,
                "text": headData
            })
        
        return outputData
    
    async def getChannelURL(chLink):
        channelID = None

        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://virtualyoutuber.fandom.com/api.php?action=parse&format=json&page={chLink.split("/")[0]}') as r:
                resp = await r.json()
                for url in resp["parse"]["externallinks"]:
                    if "https://www.youtube.com/channel/" in url and channelID is None:
                        for part in url.split("/"):
                            if 23 <= len(part) <= 25:
                                if part[0] == "U":
                                    channelID = part
        
        if channelID is None:
            return {
                "success": False
            }
        
        return {
            "success": True,
            "channelID": channelID
        }
    
    async def getAffiliate(chName):
        fandomName = (await FandomScrape.searchChannel(chName, True))["name"]
        fullPage = await FandomScrape.getChannel(fandomName, dataKey="text")
        try:
            affiliate = BeautifulSoup(fullPage, "html5lib").find("div", {"data-source": "affiliation"}).find("a").getText()
        except Exception as e:
            logging.warn(f'Failed getting affliate data for {fandomName}! Registering as "Other/Independent".', exc_info=True)
            affiliate = "Others/Independent"
        return affiliate

async def channelScrape(query: str):

    if "/channel/" in query:
        query = query.split("/")[-1]
    
    chInfo = await channelInfo(query)

    if not chInfo["success"]:
        return {
            "success": False
        }
    
    dataSource = await FandomScrape.getChannel(await FandomScrape.searchChannel(chInfo["name"], True))

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
                    result[infoGrab[entry]["dict"]] = re.sub('\[\d+\]', '', BeautifulSoup(data["data"]["value"], "html5lib").text.replace('\n', ''))
                    infoPresent = True
        if not infoPresent:
            result[infoGrab[entry]["dict"]] = None
    
    return result

def sInfoAdapter(cid):
    cData = asyncio.run(FandomScrape.getAffiliate("temma"))
    print(cData)

if __name__ == "__main__":
    sInfoAdapter(sys.argv[1])
