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

import yaml
import discord
import mysql.connector
from typing import Union
from discord.ext import commands

async def refreshWebhook(bot: commands.Bot, server: discord.Guild, channel: discord.TextChannel, db: mysql.connector.MySQLConnection = None):
    if not db:
        db = await botdb.getDB()

    server = await dbTools.serverGrab(bot, str(server.id), str(channel.id), ("url",), db)
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.user.id == bot.user.id:
            await webhook.delete()
    
    with open("yagoo.jpg", "rb") as image:
        webhook = await channel.create_webhook(name="Yagoo", avatar=image.read())
    
    await botdb.addData((str(channel.id), webhook.url), ("channel", "url"), "servers", db)

class dbTools:
    """
    Database tools for usage in other commands.
    """
    async def serverGrab(bot: commands.Bot, server: str, channel: str, dataTypes: tuple, db: mysql.connector.MySQLConnection):
        """
        Grab the channel's data if it exists, and creates and entry in the database if otherwise.
        
        Arguments
        ---
        bot: The Discord bot.
        server: The ID of the Discord server that executed the command.
        channel: The ID of the Discord channel that executed the command.
        dataTypes: The data types that should be retrieved from the database for the channel.
        db: A MySQL connection to reduce the amount of unnecessary connections.
        
        Returns
        ---
        A `dict` with `dataTypes` as keys.
        """
        while True:
            chData = await botdb.getData(channel, "channel", dataTypes, "servers", db)
            if chData is None:
                chObj = bot.get_channel(int(channel))
                with open("yagoo.jpg", "rb") as image:
                    webhook = await chObj.create_webhook(name="Yagoo", avatar=image.read(), reason="To post notifications to this channel.")
                await botdb.addData((server, channel, webhook.url, "{}"), ("server", "channel", "url", "notified"), "servers", db, index=1)
            else:
                return chData

class botdb:
    """
    Communication layer for the bot to communicate to it's MySQL database.
    """
    async def getDB():
        """
        Returns a `MySQLConnection` object to be used for database queries/modifications.
        """
        with open("settings.yaml") as f:
            db = (yaml.load(f, Loader=yaml.SafeLoader))["sql"]
        
        return mysql.connector.connect(
            host=db["host"],
            username=db["username"],
            password=db["password"],
            database=db["database"],
            buffered=True
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
        db: An existing MySQL connection to avoid making a new uncesssary connection.

        Returns
        ---
        `True` if the key exists, `False` if otherwise.
        """
        if db is None:
            db = await botdb.getDB()
        cursor = db.cursor()

        sql = f"SELECT {keyType} FROM {table} WHERE {keyType} = %s"
        arg = (key,)
        cursor.execute(sql, arg)

        if cursor.fetchone() is None:
            return False
        return True
        
    
    async def addData(data: tuple, dataTypes: tuple, table: str, db: mysql.connector.MySQLConnection = None, index = 0):
        """
        Adds data to a table in the bot's database.
        Inserts a new row if the data does not exist, and updates the data if otherwise.

        Arguments
        ---
        data: A tuple containing the data that will be inserted/updated in the table.
        dataTypes: A tuple containing all data types (ID, Name, etc.).
        table: The table which the data will be inserted/updated in.
        db: An existing MySQL connection to avoid making a new uncesssary connection.
        index: Index of item to be used as existing reference on the database.
        """
        if db is None:
            db = await botdb.getDB()
        exists = await botdb.checkIfExists(data[index], dataTypes[index], table, db)
        cursor = db.cursor()

        if exists:
            for key, keyType in zip(data, dataTypes):
                sql = f"UPDATE {table} SET {keyType} = %s WHERE {dataTypes[index]} = '{data[index]}'"
                arg = (key,)
                cursor.execute(sql, arg)
        else:
            sql = f"INSERT INTO {table} ("
            for x in dataTypes:
                sql += f"{x}, "
            sql = sql.strip(", ") + ") VALUES ("
            for x in dataTypes:
                sql += "%s, "
            sql = sql.strip(", ") + ")"
            arg = data
            cursor.execute(sql, arg)
        
        db.commit()
        return
    
    async def addMultiData(data: list, dataTypes: tuple, table: str, db: mysql.connector.MySQLConnection = None, index = 0):
        """
        Performs the same actions as `addData` but commits after all insert/update queries are executed.

        Arguments
        ---
        data: A list containing tuples which contain the data that will be inserted/updated in the table.
        dataTypes: A tuple containing all data types (ID, Name, etc.).
        table: The table which the data will be inserted/updated in.
        db: An existing MySQL connection to avoid making a new uncesssary connection.
        index: Index of item to be used as existing reference on the database.
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
            updSQL.append(f"UPDATE {table} SET {keyType} = %s WHERE {dataTypes[index]} = %s")
        
        if db is None:
            db = await botdb.getDB()
        cursor = db.cursor()

        for item in data:
            exists = await botdb.checkIfExists(item[index], dataTypes[index], table, db)

            if exists:
                i = 0
                for query in updSQL:
                    cursor.execute(query, (str(item[i]), item[index]))
                    i += 1
            else:
                cursor.execute(insSQL, item)
        
        db.commit()
        return
    
    async def deleteCell(cellType: str, rowKey: str, rowKeyType: str, table: str, db: mysql.connector.MySQLConnection = None):
        """
        Deletes the cell on the row where the key and it's type specified exists.

        Arguments
        ---
        cellType: The column/data type of the cell to be deleted
        rowKey: Data in the column/data type specified in `rowKeyType`.
        rowKeyType: Column/Data type which correlates to the data from `rowKey`.
        table: Table which contains the cell to be deleted.
        db: An existing MySQL connection to avoid making a new uncesssary connection.
        """
        if db is None:
            db = await botdb.getDB()
        cursor = db.cursor()

        cursor.execute(f"UPDATE {table} SET {cellType} = NULL WHERE {rowKeyType} = %s", (rowKey, ))
        db.commit()
        return
    
    async def deleteRow(rowKey: str, rowKeyType: str, table: str, db: mysql.connector.MySQLConnection = None):
        """
        Deletes the row containing the key and it's type specified.

        Arguments
        ---
        rowKey: Data in the column/data type specified in `rowKeyType`.
        rowKeyType: Column/Data type which correlates to the data from `rowKey`.
        table: Table which contains the data to be deleted.
        db: An existing MySQL connection to avoid making a new uncesssary connection.
        """
        if db is None:
            db = await botdb.getDB()
        cursor = db.cursor()

        cursor.execute(f"DELETE FROM {table} WHERE {rowKeyType} = %s", (rowKey, ))
        db.commit()
        return

    async def deleteMultiRow(rowKey: list, rowKeyType: str, table: str, db: mysql.connector.MySQLConnection = None):
        """
        Performs the same actions as `deleteData` but commits after all delete queries are executed.

        Arguments
        ---
        rowKey: A list containing data keys in the column/data type specified in `rowKeyType`.
        rowKeyType: Column/Data type which correlates to the data keys from `rowKey`.
        table: Table which contains the data to be deleted.
        db: An existing MySQL connection to avoid making a new uncesssary connection.
        """
        if db is None:
            db = await botdb.getDB()
        cursor = db.cursor()

        for key in rowKey:
            cursor.execute(f"DELETE FROM {table} WHERE {rowKeyType} = %s", (key, ))
        db.commit()
        return
    
    async def getData(key: str, keyType: str, returnType: tuple, table: str, db: mysql.connector.MySQLConnection = None) -> dict:
        """
        Gets the data related to the key given with the key types specified.

        Arguments
        ---
        key: The key that is present on the row being retrieved.
        keyType: The column/key type that correlates to `key`.
        returnType: Column(s)/Key type(s) to be returned once the data is retrieved.
        table: Table containing the data to be retrieved.
        db: An existing MySQL connection to avoid making a new uncesssary connection.
        
        Returns
        ---
        Dictionary that contains the key with the `returnType` specified.
        """
        if db is None:
            db = await botdb.getDB()
        cursor = db.cursor(dictionary=True)

        sql = "SELECT "
        for column in returnType:
            sql += f"{column}, "
        sql = sql.strip(", ") + f" FROM {table} WHERE {keyType} = %s"

        cursor.execute(sql, (key, ))
        return cursor.fetchone()
    
    async def getMultiData(keyList: list, keyType: str, returnType: tuple, table: str, db: mysql.connector.MySQLConnection = None) -> dict:
        """
        Performs `getData` for multiple rows, reducing load on the database server.
        
        Arguments
        ---
        keyList: The key that is present on the row being retrieved.
        keyType: The column/key type that correlates to `key`.
        returnType: Column(s)/Key type(s) to be returned once the data is retrieved.
        table: Table containing the data to be retrieved.
        db: An existing MySQL connection to avoid making a new uncesssary connection.
        
        Returns
        ---
        Dictionary with key from `keyType` as main subdict, and `returnType` keys as keys in the subdict.
        """
        if db is None:
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

    async def getAllData(table: str, keyTypes: tuple = None, filterKey: str = None, filterType: str = None, keyDict: str = None, db: mysql.connector.MySQLConnection = None):
        """
        Performs `getData` but gets all rows available in the table with te keyTypes if specified.
        
        Arguments
        ---
        table: The table containing the keys to be retrieved.
        keyTypes: A tuple to filter key types if necessary.
        filter: Contents of the filter key to filter needed rows.
        filterType: The data type of the filter key.
        keyDict: Key type to be made as main key if a dictionary is needed instead of a list or tuple.
        db: An existing MySQL connection to avoid making a new uncesssary connection.
        
        Returns
        ---
        A `dict` or `tuple` (`dict` is supplied when `keyDict` is supplied) that contains the data.
        """
        if db is None:
            db = await botdb.getDB()
        
        if keyTypes is None:
            cursor = db.cursor()
            
            sql = f"SELECT * FROM {table}"
        else:
            cursor = db.cursor(dictionary=True)
            
            sql = "SELECT "
            for dataType in keyTypes:
                sql += f"{dataType}, "
            sql = sql.strip(", ") + f" FROM {table}"
        
        if filterKey is not None:
            sql += f" WHERE {filterType} = %s"
            cursor.execute(sql, (filterKey, ))
        else:
            cursor.execute(sql)
        if keyDict:
            result = {}
            for item in cursor.fetchall():
                mainKey = item[keyDict]
                item.pop(keyDict)
                result[mainKey] = item
            return result
        return cursor.fetchall()
    
    async def listConvert(data: Union[str, list]):
        """
        Converts a list to a formatted string for data updates.
        Works in the opposite way too.
        
        Arguments
        ---
        data: Data to be converted to a formatted string or list.
        
        Returns
        ---
        The data that is converted to a formatted string or a list. 
        `None` if no data is passed through.
        """
        seperator = "|yb|"
        
        if isinstance(data, list):
            return seperator.join(data).strip("|yb|")
        if data is None:
            return None
        return data.split(seperator)
