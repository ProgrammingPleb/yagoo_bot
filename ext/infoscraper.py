import json
import aiohttp
import asyncio
import re
import sys
import logging
import yaml
import tweepy
from bs4 import BeautifulSoup
from typing import Union
from .share.botUtils import formatMilestone, premiereScrape

async def streamInfo(channelId: Union[str, int]):
    output = None

    consent = {'CONSENT': 'YES+cb.20210328-17-p0.en+FX+162'}
    async with aiohttp.ClientSession(cookies=consent) as session:
        with open("data/settings.yaml") as f:
            settings = yaml.load(f, Loader=yaml.SafeLoader)

        if settings["proxy"]:
            proxy = f"http://{settings['proxyIP']}:{settings['proxyPort']}"
            proxyauth = aiohttp.BasicAuth(settings["proxyUsername"], settings["proxyPassword"])
        else:
            proxy = None
            proxyauth = None
        async with session.get(f'https://www.youtube.com/channel/{channelId}/live?hl=en-US', proxy=proxy, proxy_auth=proxyauth) as r:
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
                            if videoInfo["isLive"] and ("watching now" in videoInfo["viewCount"]["runs"][-1]["text"]):
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
                                    "timeText": morevInfo["dateText"]["simpleText"].replace('Started streaming ', ''),
                                    "videoInfo": videoInfo["viewCount"]["runs"]
                                }
                            else:
                                output = {
                                    "isLive": False,
                                    "text": "Schedule Livestream",
                                    "channel": channelId,
                                    "videoInfo": videoInfo["viewCount"]["runs"],
                                }
    if not output:
        output = {
            "isLive": False,
            "text": "No Output",
            "channel": channelId
        }
    return output

async def channelInfo(channelId: Union[str, int], scrape = False, debug: bool = False):
    channelData = None

    if scrape:
        consent = {'CONSENT': 'YES+cb.20210328-17-p0.en+FX+162'}
        async with aiohttp.ClientSession(cookies=consent) as session:
            with open("data/settings.yaml") as f:
                settings = yaml.load(f, Loader=yaml.SafeLoader)

            if settings["proxy"]:
                proxy = f"http://{settings['proxyIP']}:{settings['proxyPort']}"
                proxyauth = aiohttp.BasicAuth(settings["proxyUsername"], settings["proxyPassword"])
            else:
                proxy = None
                proxyauth = None
            async with session.get(f'https://www.youtube.com/channel/{channelId}?hl=en-US', proxy=proxy, proxy_auth=proxyauth) as r:
                soup = BeautifulSoup(await r.text(), "html5lib")
                scripts = soup.find_all("script")
                for script in scripts:
                    if ("var ytInitialData" in script.getText()) or ('window["ytInitialData"]' in script.getText()):
                        ytdata = json.loads(script.getText().replace(';', '').replace('var ytInitialData = ', '').replace('window["ytInitialData"]', ''))

                        # Check Subscriber Count
                        cSubsA, cSubsR = await formatMilestone(ytdata["header"]["c4TabbedHeaderRenderer"]["subscriberCountText"]["simpleText"])

                        # Get premieres (if any)
                        premieres = await premiereScrape(ytdata)

                        channelData = {
                            "id": channelId,
                            "name": ytdata["metadata"]["channelMetadataRenderer"]["title"],
                            "image": ytdata["metadata"]["channelMetadataRenderer"]["avatar"]["thumbnails"][0]["url"],
                            "realSubs": cSubsA,
                            "roundSubs": cSubsR,
                            "success": True,
                            "premieres": premieres
                        }

                        try:
                            channelData["banner"] = ytdata["header"]["c4TabbedHeaderRenderer"]["banner"]["thumbnails"][3]["url"]
                        except Exception as e:
                            channelData["banner"] = None

                        try:
                            channelData["mbanner"] = ytdata["header"]["c4TabbedHeaderRenderer"]["banner"]["thumbnails"][1]["url"]
                        except Exception as e:
                            channelData["mbanner"] = None

                        if "headerLinks" in ytdata["header"]["c4TabbedHeaderRenderer"]:
                            found = False
                            for link in ytdata["header"]["c4TabbedHeaderRenderer"]["headerLinks"]["channelHeaderLinksRenderer"]["primaryLinks"]:
                                if "twitter.com" in link["navigationEndpoint"]["urlEndpoint"]["url"] and not found:
                                    channelData["twitter"] = link["navigationEndpoint"]["urlEndpoint"]["url"].split("&q=")[-1].split("%2F")[-1].split("%3F")[0]
                                    found = True
                            if not found and "secondaryLinks" in ytdata["header"]["c4TabbedHeaderRenderer"]["headerLinks"]["channelHeaderLinksRenderer"]:
                                for link in ytdata["header"]["c4TabbedHeaderRenderer"]["headerLinks"]["channelHeaderLinksRenderer"]["secondaryLinks"]:
                                    if "twitter.com" in link["navigationEndpoint"]["urlEndpoint"]["url"] and not found:
                                        channelData["twitter"] = link["navigationEndpoint"]["urlEndpoint"]["url"].split("&q=")[-1].split("%2F")[-1].split("%3F")[0]
                if channelData is None:
                    with open(f"debug/{channelId}.html", "w") as f:
                        f.write(await r.text())
                    logging.warn(f"Unable to get ytInitialData for {channelId}!")
    else:
        try:
            with open("data/scrape.json", encoding="utf-8") as f:
                channels = json.load(f)

            channelData = channels[channelId]
        except Exception as e:
            logging.error("Info Scraper - An error has occurred!", exc_info=True)

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
                matched = False
                for title in resp[1]:
                    for name in chNSplit:
                        if name.lower() in title.lower() and ('(disambiguation)') not in title.lower() and len(title.split("/")) < 2 and not matched:
                            chRName = title
                            matched = True
                    if len(title.split("/")) < 2 and ('(disambiguation)') not in title.lower():
                        nameList.append(title)
                    x += 1
                if not matched:
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
                else:
                    chLink = {
                        "status": "Success",
                        "name": chRName,
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

    async def getThumbnail(dataText) -> str:
        soup = BeautifulSoup(dataText, "html5lib")
        imgTag = soup.find("img", {"class": "pi-image-thumbnail"})

        return imgTag["src"]

    async def getAffiliate(chName) -> str:
        fandomName = (await FandomScrape.searchChannel(chName, True))["name"]
        fullPage = await FandomScrape.getChannel(fandomName, dataKey="text")
        try:
            affiliate = BeautifulSoup(fullPage, "html5lib").find("div", {"data-source": "affiliation"}).find("a").getText()
        except Exception as e:
            logging.warn(f'Failed getting affliate data for {fandomName}! Registering as "Other/Independent".', exc_info=True)
            affiliate = "Others/Independent"
        return affiliate

    async def getSections(dataText) -> list:
        soup = BeautifulSoup(dataText, "html5lib")

        pastInfobox = False
        sections = []
        for h2 in soup.find_all("h2"):
            sName = h2.getText().replace("[edit | edit source]", "")
            if sName.lower() in ("External Links".lower(), "References".lower()):
                continue
            if pastInfobox:
                sections.append(sName)
            if sName.lower() == "Introduction Video".lower():
                pastInfobox = True

        return sections

    async def getSectionData(dataText, sections) -> list:
        soup = BeautifulSoup(dataText, "html5lib")

        data = []
        for h2 in soup.find_all("h2"):
            sName = h2.getText().replace("[edit | edit source]", "")

            try:
                if sName in sections:
                    pList = []
                    lastElement = h2.find_next_sibling()

                    while True:
                        if lastElement.name == "p":
                            pList.append(re.sub(r'\[[^()]*\]', '', lastElement.getText().strip()))
                            lastElement = lastElement.find_next_sibling()
                        elif lastElement.name == "ul":
                            pList = await FandomScrape.getPointers(lastElement)
                            break
                        elif lastElement.name == "h3":
                            pList = await FandomScrape.getSubSections(lastElement)
                            break
                        elif lastElement.name == "figure":
                            lastElement = lastElement.find_next_sibling()
                        else:
                            break

                    data.append({'name': sName, 'text': pList})
            except Exception as e:
                logging.error("Fandom Scrape - An error has occured!", exc_info=True)
                #print(f"Info Scraper - Unable to get text for {sName}!")
                #traceback.print_exception(type(e), e, e.__traceback__)

        return data

    async def getSubSections(lastElement) -> dict:
        subSections = []
        subHeader = None
        subPoints = []

        while True:
            if lastElement.name == "h3":
                if len(subPoints) != 0:
                    subSections.append({subHeader: subPoints})
                subHeader = lastElement.getText().replace("[edit | edit source]", "")
                subPoints = []
            elif lastElement.name == "p":
                subPoints.append(re.sub(r'\[[^()]*\]', '', lastElement.getText().strip()))
            elif lastElement.name == "ul":
                subPoints.append(await FandomScrape.getPointers(lastElement))
            elif lastElement.name == "h2":
                if len(subPoints) != 0:
                    subSections.append({subHeader: subPoints})
                break
            lastElement = lastElement.find_next_sibling()

        return subSections

    async def getPointers(lastElement) -> list:
        subPointers = []

        if lastElement.name == "ul":
            liTags = lastElement.find_all("li", recursive=False)
        else:
            return

        for tag in liTags:
            subPointers.append(await FandomScrape.getSubPointers(tag))

        return [subPointers]

    async def getSubPointers(tag):
        subPointers = None

        if tag.find("ul", recursive=False) == None:
            subPointers = re.sub(r'\[[^()]*\]', '', tag.getText()).strip()
        else:
            subPointers = {"point": re.sub(r'\[[^()]*\]', '', tag.getText()).strip()}
            tempPointers = []
            for tag in tag.find("ul", recursive=False).find_all("li", recursive=False):
                tempPointers.append(await FandomScrape.getSubPointers(tag))
            for text in tempPointers:
                if text in subPointers["point"]:
                    subPointers["point"] = subPointers["point"].replace(text, "").strip()
            subPointers["subPoints"] = tempPointers

        return subPointers

class TwitterScrape:
    async def getCredentials():
        with open("data/settings.yaml") as f:
            settings = yaml.load(f, Loader=yaml.SafeLoader)

        return settings["twitter"]

    async def getAPI():
        credentials = await TwitterScrape.getCredentials()

        auth = tweepy.OAuthHandler(credentials["apiKey"], credentials["apiSecret"])
        auth.set_access_token(credentials["accessKey"], credentials["accessSecret"])

        # Return API object
        return tweepy.API(auth, wait_on_rate_limit=True)

    async def getUserID(screenName):
        api = await TwitterScrape.getAPI()
        return (api.get_user(screen_name=screenName)).id_str
    
    async def getUserDetails(screenName):
        api = await TwitterScrape.getAPI()
        return api.get_user(screen_name=screenName)

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
    cData = asyncio.run(channelInfo("UCNVEsYbiZjH5QLmGeSgTSzg", True))
    print(cData)

if __name__ == "__main__":
    sInfoAdapter(sys.argv[1])
