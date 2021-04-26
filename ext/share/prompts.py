import asyncio
import traceback
from typing import Union
import discord
from discord.ext import commands
from discord_slash.context import SlashContext

async def subCheck(ctx, bot, subMsg, mode, chName):
    from ext.share.botUtils import serverSubTypes
    subOptions = ["Livestream", "Milestone", "Premiere", "All"]
    subText = ""
    subChoice = []
    subNum = 1

    for sub in subOptions:
        subText += f"{subNum}. {sub} Notifications\n"
        subChoice.append(str(subNum))
        subNum += 1
    
    if mode == 1:
        action = "Subscribe"
    elif mode == 2:
        action = "Unsubscribe"
    else:
        return {
            "success": False
        }
    
    subEmbed = discord.Embed(title=chName, description=f"{action} to the channel's:\n\n"
                                                        f"{subText}X. Cancel\n\n[Bypass this by setting the channel's default subscription type using `y!subdefault`.\n"
                                                        "Select multiple subscriptions by seperating them using commas, for example `1,3`.]")

    await subMsg.edit(content=None, embed=subEmbed)

    uInput = {
        "success": False
    }

    def check(m):
        return (m.content.lower() in subChoice + ['x'] or "," in m.content) and m.author == ctx.author

    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await subMsg.delete()
            break
        else:
            await msg.delete()
            if msg.content in subChoice or ("," in msg.content and "x" not in msg.content.lower()):
                if subChoice[-1] not in msg.content.split(","):
                    sSubType = await serverSubTypes(msg, subChoice + ['x'], subOptions)
                    uInput["subType"] = sSubType["subType"]
                else:
                    subTypes = []
                    for sub in subOptions:
                        if sub != subOptions[-1]:
                            subTypes.append(sub.lower())
                    uInput["subType"] = subTypes
                uInput["success"] = True
                break
            elif msg.content.lower() == 'x':
                break
    
    return uInput

async def unsubCheck(ctx: Union[commands.Context, SlashContext], bot: commands.Bot, chData: dict, unsubMsg: discord.Message):
    notifCount = 1
    embedChoice = []
    unsubEmbed = discord.Embed(title=chData["name"], description="Unsubscribe from this channel's:\n")
    
    for subType in chData["subType"]:
        unsubEmbed.description += f"{notifCount}. {subType.capitalize()} Notifications\n"
        embedChoice.append(str(notifCount))
        notifCount += 1
    unsubEmbed.description += "\nX. Cancel\n[Select multiple subscriptions by seperating them using commas, for example `1,3`.]"

    await unsubMsg.edit(content=None, embed=unsubEmbed)


    def check(m):
        return (m.content.lower() in embedChoice + ["x"] or "," in m.content) and m.author == ctx.author

    while True:
        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "subType": None
            }
        await msg.delete()
        if msg.content in embedChoice:
            return {
                "success": True,
                "subType": [chData["subType"][int(msg.content) - 1]]
            }
        elif "," in msg.content and "x" not in msg.content.lower():
            valid = True
            returnData = {
                    "success": False,
                    "subType": []
                }
            for subType in msg.content.split(","):
                if valid:
                    try:
                        returnData["subType"].append(chData["subType"][int(subType) - 1])
                    except Exception as e:
                        valid = False
                else:
                    break
            if valid:
                returnData["success"] = True
                return returnData
        elif "x" in msg.content.lower():
            return {
                "success": False,
                "subType": None
            }

async def botError(ctx, error):
    errEmbed = discord.Embed(title="An error has occurred!", color=discord.Colour.red())
    if "403 Forbidden" in str(error):
        permData = [{
            "formatName": "Manage Webhooks",
            "dataName": "manage_webhooks"
        }, {
            "formatName": "Manage Messages",
            "dataName": "manage_messages"
        }]
        permOutput = []
        for perm in iter(ctx.guild.me.permissions_in(ctx.channel)):
            for pCheck in permData:
                if perm[0] == pCheck["dataName"]:
                    if not perm[1]:
                        permOutput.append(pCheck["formatName"])
        plural = "this permission"
        if len(permOutput) > 1:
            plural = "these permissions"
        errEmbed.description = "This bot has insufficient permissions for this channel.\n" \
                               f"Please allow the bot {plural}:\n"
        for perm in permOutput:
            errEmbed.description += f'\n - `{perm}`'
    if "Missing Arguments" in str(error):
        errEmbed.description = "A command argument was not given when required to."
    if "No Subscriptions" in str(error):
        errEmbed.description = "There are no subscriptions for this channel.\n" \
                               "Subscribe to a channel's notifications by using `y!sub` or `/sub` command."
    if isinstance(error, commands.CheckFailure):
        errEmbed.description = "You are missing permissions to use this bot.\n" \
                               "Ensure that you have one of these permissions for the channel/server:\n\n" \
                               " - `Administrator (Server)`\n - `Manage Webhooks (Channel/Server)`"

    if type(error) != str:
        print("An unknown error has occurred.")
        traceback.print_exception(type(error), error, error.__traceback__)
        print(error)
    
    return errEmbed

async def searchPrompt(ctx, bot, sResults: list, smsg, embedDesc):
    sEmbed = discord.Embed(title="VTuber Search", description=embedDesc)
    sDesc = ""
    checkNum = []
    picked = False
    pickName = None

    x = 1
    for entry in sResults:
        sDesc += f'{x}. {entry}\n'
        checkNum.append(str(x))
        x += 1
        
    sEmbed.add_field(name="Search Results", value=sDesc.strip(), inline=False)
    sEmbed.add_field(name="Other Actions", value="X. Cancel", inline=False)

    await smsg.edit(content=None, embed=sEmbed)

    def check(m):
        return m.content.lower() in checkNum + ['x'] and m.author == ctx.author
    
    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await smsg.delete()
            break
        if msg.content in checkNum:
            await msg.delete()
            pickName = sResults[int(msg.content) - 1]
            picked = True
            break
        elif msg.content.lower() == 'x':
            await msg.delete()
            break
        else:
            await msg.delete()
    
    if not picked:
        return {
            "success": False
        }
    
    return {
        "success": True,
        "name": pickName
    }

async def searchConfirm(ctx, bot, sName: str, smsg, embedDesc, accept, decline, url: bool = False):
    sEmbed = discord.Embed(title="VTuber Search", description=embedDesc)
    if not url:
        sEmbed.add_field(name="Actions", value=f"Y. {accept}\nN. {decline}\nX. Cancel", inline=False)
        choices = ["y", "n", "x"]
    else:
        sEmbed.add_field(name="Actions", value=f"Y. {accept}\nX. Cancel", inline=False)
        choices = ["y", "x"]

    await smsg.edit(content=None, embed=sEmbed)

    def check(m):
        return m.content.lower() in choices and m.author == ctx.author
    
    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "declined": False
            }
        if msg.content.lower() == "y":
            await msg.delete()
            return {
                "success": True,
                "declined": False
            }
        if msg.content.lower() == "n":
            await msg.delete()
            return {
                "success": False,
                "declined": True
            }
        if msg.content.lower() == "x":
            await msg.delete()
            return {
                "success": False,
                "declined": False
            }
        await msg.delete()

async def ctgPicker(ctx, bot, channels, ctgMsg):
    catStr = ""
    categories = []
    catNum = []
    x = 1
    for channel in channels:
        if channels[channel]["category"] not in categories:
            catStr += f'{x}. {channels[channel]["category"]}\n'
            categories.append(channels[channel]["category"])
            catNum.append(str(x))
            x += 1
        
    catEmbed = discord.Embed(title="Channel Search", description="Choose the affiliation corresponding to the VTuber:\n"
                                                                 "If the affiliation is not in this list,search the VTuber to add it to the bot's database.")
    catEmbed.add_field(name="Affiliation", value=catStr.strip())
    catEmbed.add_field(name="Other Actions", value="S. Search for a VTuber\nX. Cancel")

    await ctgMsg.edit(content=None, embed=catEmbed)

    def check(m):
        return m.content.lower() in catNum + ["s", "x"] and m.author == ctx.author
    
    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "search": False
            }
        if msg.content in catNum:
            await msg.delete()
            return {
                "success": True,
                "search": False,
                "category": categories[int(msg.content) - 1]
            }
        if msg.content.lower() == "s":
            await msg.delete()
            return {
                "success": False,
                "search": True
            }
        if msg.content.lower() == "x":
            await msg.delete()
            return {
                "success": False,
                "search": False
            }
        await msg.delete()

async def searchMessage(ctx, bot, srchMsg):
    searchEmbed = discord.Embed(title="VTuber Search")
    searchEmbed.description = "Enter a VTuber name:\n" \
                              "[Enter `cancel` to cancel searching.]"
    
    await srchMsg.edit(content=None, embed=searchEmbed)

    def check(m):
        return m.author == ctx.author
    
    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "search": None
            }
        if msg.content.lower() == "cancel":
            await msg.delete()
            return {
                "success": False,
                "search": None
            }
        await msg.delete()
        return {
            "success": True,
            "search": msg.content
        }
