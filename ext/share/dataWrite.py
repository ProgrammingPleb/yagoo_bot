import logging

async def genServer(servers, cserver, cchannel):
    if str(cserver.id) not in servers:
        logging.debug("New server! Adding to database.")
        servers[str(cserver.id)] = {
            str(cchannel.id): {
                "url": "",
                "notified": {},
                "livestream": [],
                "milestone": []
            }
        }
    elif str(cchannel.id) not in servers[str(cserver.id)]:
        logging.debug("New channel in server! Adding to database.")
        servers[str(cserver.id)][str(cchannel.id)] = {
            "url": "",
            "notified": {},
            "livestream": [],
            "milestone": []
        }
    
    return servers
