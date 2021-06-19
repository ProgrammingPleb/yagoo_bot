import json
import yaml
import asyncio
import logging
import discord
import mysql.connector
from typing import Union
from discord.ext import commands
from ext.share.prompts import botError
from .botUtils import msgDelete, serverSubTypes
from .botVars import allSubTypes

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

async def getSubType(ctx: commands.Context, mode, bot: commands.Bot, prompt = None):
    pEmbed = discord.Embed()
    subDNum = 1
    subOptions = allSubTypes()
    subChoice = []

    with open("data/servers.json") as f:
        servers = json.load(f)

    if mode == 1:
        
        subEText = "Toggle:\n\n"
        if "subDefault" in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
            for subType in subOptions:
                if subType.lower() in servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]:
                    subEText += f"{subDNum}. {subType} Notifications 🟢\n"
                else:
                    subEText += f"{subDNum}. {subType} Notifications 🔴\n"
                subChoice.append(str(subDNum))
                subDNum += 1
        else:
            for subType in subOptions:
                subEText += f"{subDNum}. {subType} Notifications 🔴\n"
                subChoice.append(str(subDNum))
                subDNum += 1
        subEText += f"{subDNum}. All Notifications\nX. Cancel\n\n[Toggle multiple defaults by seperating them using commas, for example `1,3`.]"

        subChoice += [str(subDNum), 'x']

        pEmbed.title = "Default Channel Subscriptions"
        pEmbed.description = subEText
        def check(m):
            return (m.content.lower() in subChoice or ',' in m.content) and m.author == ctx.author
        prompt = await ctx.send(embed=pEmbed)
    elif mode == 2:
        subEText = "Get subscription list for:\n\n"

        valid = False
        actualSubTypes = []
        for serverKey in servers[str(ctx.guild.id)][str(ctx.channel.id)]:
            if serverKey.capitalize() in subOptions:
                if servers[str(ctx.guild.id)][str(ctx.channel.id)][serverKey] != []:
                    actualSubTypes.append(serverKey.capitalize())
                    valid = True

        if not valid:
            await ctx.send(embed = await botError(ctx, "No Subscriptions"))
            return {
                "success": False
            }

        for subType in actualSubTypes:
            subEText += f"{subDNum}. {subType} Notifications\n"
            subChoice.append(str(subDNum))
            subDNum += 1
        subEText += "X. Cancel\n\n[Bypass this by setting the channel's default subscription type using `y!subdefault`.]"
        subChoice += ['x']

        pEmbed.title = "Channel Subscription Type"
        pEmbed.description = subEText
        def check(m):
            return m.content.lower() in subChoice and m.author == ctx.author
        await prompt.edit(content=" ", embed=pEmbed)

    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await prompt.delete()
            await ctx.message.delete()
            return {
                "success": False
            }
        else:
            await msg.delete()
            if (msg.content.lower() in subChoice or "," in msg.content) and 'x' not in msg.content.lower():
                if mode == 1:
                    subUChoice = await serverSubTypes(msg, subChoice, subOptions)

                    if subUChoice["success"]:
                        try:
                            for subUType in subUChoice["subType"]:
                                if subUType not in servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]:
                                    servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"].append(subUType)
                                else:
                                    servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"].remove(subUType)
                        except KeyError:
                            servers = await genServer(servers, ctx.guild, ctx.channel)
                            servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"] = subUChoice["subType"]
                        with open("data/servers.json", "w") as f:
                            json.dump(servers, f, indent=4)
                        
                        subText = ""
                        if len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) == 2:
                            subText = f"{servers[str(ctx.guild.id)][str(ctx.channel.id)]['subDefault'][0]} and {servers[str(ctx.guild.id)][str(ctx.channel.id)]['subDefault'][1]}"
                        elif len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) == len(subOptions):
                            subText = "all"
                        elif len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) == 1:
                            subText = servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"][0]
                        else:
                            subTypeCount = 1
                            for subUType in servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]:
                                if subTypeCount == len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]):
                                    subText += f"and {subUType}"
                                else:
                                    subText += f"{subUType}, "

                        await msgDelete(ctx)
                        if len(servers[str(ctx.guild.id)][str(ctx.channel.id)]["subDefault"]) == 0:
                            await prompt.edit(content=f"Subscription defaults for this channel has been removed.", embed=" ")
                        else:
                            await prompt.edit(content=f"This channel will now subscribe to {subText} notifications by default.", embed=" ")
                        break
                elif mode == 2:
                    if "," not in msg.content:
                        return {
                            "success": True,
                            "subType": actualSubTypes[int(msg.content) - 1].lower()
                        }
            elif msg.content.lower() == 'x':
                await prompt.delete()
                await ctx.message.delete()
                return {
                    "success": False
                }

async def getwebhook(bot, servers, cserver, cchannel):
    if isinstance(cserver, str) and isinstance(cchannel, str):
        cserver = bot.get_guild(int(cserver))
        cchannel = bot.get_channel(int(cchannel))
    try:
        logging.debug(f"Trying to get webhook url for {cserver.id}")
        whurl = servers[str(cserver.id)][str(cchannel.id)]["url"]
    except KeyError:
        logging.debug("Failed to get webhook url! Creating new webhook.")
        servers = await genServer(servers, cserver, cchannel)
        with open("yagoo.jpg", "rb") as image:
            webhook = await cchannel.create_webhook(name="Yagoo", avatar=image.read())
        whurl = webhook.url
        servers[str(cserver.id)][str(cchannel.id)]["url"] = whurl
        with open("data/servers.json", "w") as f:
            json.dump(servers, f, indent=4)
    return whurl

async def refreshWebhook(server: discord.Guild, channel: discord.TextChannel):
    with open("data/servers.json") as f:
        servers = json.load(f)

    with open("yagoo.jpg", "rb") as image:
        webhook = await channel.create_webhook(name="Yagoo", avatar=image.read())
    
    servers[str(server.id)][str(channel.id)]["url"] = webhook.url

    with open("data/servers.json", "w") as f:
        json.dump(servers, f, indent=4)

class botdb:
    async def getDB():
        """
        Returns a `MySQLConnection` object to be used for database queries/modifications.
        """
        with open("data/settings.yaml") as f:
            db = (yaml.load(f, Loader=yaml.SafeLoader))["sql"]
        
        return mysql.connector.connect(
            host=db["host"],
            username=db["username"],
            password=db["password"],
            database=db["database"]
        )
    
    async def changeToMany(data: tuple, dataTypes: tuple, table: str) -> list:
        """
        Changes multiple data in tuples to a list for use with `executemany()`.

        Arguments
        ---
        data: A tuple containing the data that will be inserted/updated in the table.
        dataTypes: A tuple containing all data types (ID, Name, etc.).
        table: The table which the data will be inserted/updated in.

        Returns
        ---
        A list which can be used with `executemany()`.
        """
        execList = []

        for key, keyType in zip(data, dataTypes):
            execList.append((table, keyType, key, dataTypes[0], data[0]))
        
        return execList

    async def checkIfExists(key: str, keyType: str, table: str, db: mysql.connector.MySQLConnection = None):
        """
        Checks if a key exists on the database.

        Arguments
        ---
        key: The value of a key on the row.
        keyType: The key header of the value (ID, Name, etc.)
        table: The table in the database that contains the row in question.

        Returns
        ---
        `True` if the key exists, `False` if otherwise.
        """
        if db is None:
            db = await botdb.getDB()
        cursor = db.cursor()

        sql = f"SELECT {keyType} FROM channels WHERE {keyType} = %s"
        arg = (key,)
        cursor.execute(sql, arg)

        if cursor.fetchone() == None:
            return False
        return True
        
    
    async def addData(data: tuple, dataTypes: tuple, table: str):
        """
        Adds data to a table in the bot's database.
        Inserts a new row if the data does not exist, and updates the data if otherwise.

        Arguments
        ---
        data: A tuple containing the data that will be inserted/updated in the table.
        dataTypes: A tuple containing all data types (ID, Name, etc.).
        table: The table which the data will be inserted/updated in.
        """
        db = await botdb.getDB()
        exists = await botdb.checkIfExists(data[0], dataTypes[0], table, db)
        cursor = db.cursor()

        if exists:
            for key, keyType in zip(data, dataTypes):
                sql = f"UPDATE {table} SET {keyType} = %s WHERE {dataTypes[0]} = '{data[0]}'"
                arg = (key,)
                cursor.execute(sql, arg)
        else:
            sql = f"INSERT INTO {table} ("
            for x in dataTypes:
                sql += f"{x}, "
            sql = sql.strip() + ") VALUES ("
            for x in dataTypes:
                sql += "%s, "
            sql = sql.strip() + ")"
            arg = data
            cursor.execute(sql, arg)
        
        db.commit()
        return
    
    async def addMultiData(data: list, dataTypes: tuple, table: str):
        """
        Performs the same actions as `addData` but commits after all insert/update queries are executed.

        Arguments
        ---
        data: A list containing tuples which contain the data that will be inserted/updated in the table.
        dataTypes: A tuple containing all data types (ID, Name, etc.).
        table: The table which the data will be inserted/updated in.
        """
        insSQL = f"INSERT INTO {table} ("
        for x in dataTypes:
            insSQL += f"{x}, "
        insSQL = insSQL.strip().strip(",") + ") VALUES ("
        for x in dataTypes:
            insSQL += "%s, "
        insSQL = insSQL.strip().strip(",") + ")"

        updSQL = []
        for keyType in dataTypes:
            updSQL.append(f"UPDATE {table} SET {keyType} = %s WHERE {dataTypes[0]} = %s")
        
        db = await botdb.getDB()
        cursor = db.cursor()

        for item in data:
            exists = await botdb.checkIfExists(item[0], dataTypes[0], table, db)

            if exists:
                i = 0
                for query in updSQL:
                    cursor.execute(query, (str(item[i]), item[0]))
                    i += 1
            else:
                cursor.execute(insSQL, item)
        
        db.commit()
        return
    
    async def deleteData(rowKey: str, rowKeyType: str, table: str):
        """
        Deletes the row containing the key and it's type specified.

        Arguments
        ---
        rowKey: Data in the column/data type specified in `rowKeyType`.
        rowKeyType: Column/Data type which correlates to the data from `rowKey`.
        table: Table which contains the data to be deleted.
        """
        db = await botdb.getDB()
        cursor = db.cursor()

        cursor.execute(f"DELETE FROM {table} WHERE {rowKeyType} = %s", (rowKey, ))
        db.commit()
        return

    async def deleteMultiData(rowKey: list, rowKeyType: str, table: str):
        """
        Performs the same actions as `deleteData` but commits after all delete queries are executed.

        Arguments
        ---
        rowKey: A list containing data keys in the column/data type specified in `rowKeyType`.
        rowKeyType: Column/Data type which correlates to the data keys from `rowKey`.
        table: Table which contains the data to be deleted.
        """
        db = await botdb.getDB()
        cursor = db.cursor()

        for key in rowKey:
            cursor.execute(f"DELETE FROM {table} WHERE {rowKeyType} = %s", (key, ))
        db.commit()
        return
    
    async def getData(key: str, keyType: str, returnType: tuple, table: str) -> dict:
        """
        Gets the data related to the key given with the key types specified.

        Arguments
        ---
        key: The key that is present on the row being retrieved.
        keyType: The column/key type that correlates to `key`.
        returnType: Column(s)/Key type(s) to be returned once the data is retrieved.
        table: Table containing the data to be retrieved.
        
        Returns
        ---
        Dictionary that contains the key with the `returnType` specified.
        """
        db = await botdb.getDB()
        cursor = db.cursor(dictionary=True)

        sql = "SELECT "
        for column in returnType:
            sql += f"{column}, "
        sql = sql.strip(", ") + f" FROM {table} WHERE {keyType} = %s"

        cursor.execute(sql, (key, ))
        return cursor.fetchone()
    
    async def getMultiData(keyList: list, keyType: str, returnType: tuple, table: str) -> dict:
        """
        Performs `getData` for multiple rows, reducing load on the database server.
        
        Arguments
        ---
        keyList: The key that is present on the row being retrieved.
        keyType: The column/key type that correlates to `key`.
        returnType: Column(s)/Key type(s) to be returned once the data is retrieved.
        table: Table containing the data to be retrieved.
        
        Returns
        ---
        Dictionary with key from `keyType` as main subdict, and `returnType` keys as keys in the subdict.
        """
        db = await botdb.getDB()
        cursor = db.cursor(dictionary=True)

        sql = "SELECT "
        for column in returnType:
            sql += f"{column}, "
        sql = sql.strip(", ") + f" FROM {table} WHERE {keyType} = %s"

        finalData = {}
        for key in keyList:
            cursor.execute(sql, (key, ))
            finalData[key] = cursor.fetchone()
        return finalData
