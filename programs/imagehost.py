import rpyc
import requests
import os
import pytz
import json
from datetime import datetime
from rpyc.utils.server import ThreadedServer

class Runner(rpyc.Service):
    def on_connect(self, conn):
        print("New Connection.")
    
    def on_disconnect(self, conn):
        print("Client Disconnected.")
    
    def exposed_thumbGrab(self, cid, url):
        print(f'Getting thumbnail for {cid}: {url}')
        if not os.path.exists("data"):
            print("Creating data directory...")
            os.mkdir("data")
        print("Checking in database if thumbnail already exists.")
        try:
            with open("data/imagehost.json") as f:
                channels = json.load(f)
        except (json.decoder.JSONDecodeError, FileNotFoundError):
            channels = {}
        if cid not in channels:
            channels[cid] = {
                "ytURL": "",
                "uploadURL": ""
            }
        if url != channels[cid]["ytURL"]:
            print("Downloading and uploading thumbnail...")
            timeStr = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%m%d%y-%H%M")
            if not os.path.exists(f'/ezzmoe/yagoo/images/{cid}'):
                os.mkdir(f'/ezzmoe/yagoo/images/{cid}')
            with open(f'/ezzmoe/yagoo/images/{cid}/{timeStr}.png', 'wb') as f:
                with requests.get(url) as r:
                    f.write(r.content)
            
            thumbnailURL = f'https://yagoo.ezz.moe/thumbnail/{cid}/{timeStr}.png'

            channels[cid]["ytURL"] = url
            channels[cid]["uploadURL"] = thumbnailURL

            with open("data/imagehost.json", "w") as f:
                json.dump(channels, f, indent=4)

            print(f'Uploaded thumbnail to: {thumbnailURL}')
        else:
            print("Thumbnail is already downloaded! Returning existing URL.")
            thumbnailURL = channels[cid]["uploadURL"]
        return thumbnailURL

    def exposed_srvstop(self):
        t.close()


if __name__ == "__main__":
    with requests.get("https://api.ipify.org/") as r:
        publicIP = r.text
    if publicIP != "":
        print(f'Server now running with IP {publicIP} on port 25565.')
        t = ThreadedServer(Runner, port=25565)
        t.start()
    else:
        print("Public IP not found! Aborting...")
