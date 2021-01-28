import json, pytz
from datetime import datetime

async def bdayCheck():
    update = False
    write = False
    bdayResults = {}

    with open("data/bot.json") as f:
        bdata = json.load(f)
    
    if "bdayCheck" not in bdata:
        bdata["bdayCheck"] = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%m%d")
        write = True

    now = datetime.now(pytz.timezone("Asia/Tokyo")).replace(hour=0, minute=0, second=0, microsecond=0)
    if pytz.timezone("Asia/Tokyo").localize(datetime.strptime(bdata["bdayCheck"], "%m%d").replace(year=datetime.now(pytz.timezone("Asia/Tokyo")).year)) < now:
        with open("data/birthdays.json") as f:
            bdays = json.load(f)

        if str(now.day) in bdays[str(now.month)]:
            bdayCurrent = bdays[str(now.month)][str(now.day)]
            update = True
        
        bdata["bdayCheck"] = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%m%d")
        write = True
    
    if write:
        with open("data/bot.json") as f:
            json.dump(bdata, f)
    
    if update:
        return {
            "occurToday": update,
            "bdayData": bdayCurrent
        }
    else:
        return {
            "occurToday": update
        }
