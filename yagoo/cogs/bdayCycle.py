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
import pytz
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

    return {
        "occurToday": update
    }
