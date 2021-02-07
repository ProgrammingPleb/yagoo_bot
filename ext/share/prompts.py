import asyncio
import traceback
import discord
from discord.ext import commands

async def subCheck(ctx, bot, subMsg, mode, chName):
    if mode == 1:
        action = "Subscribe"
    elif mode == 2:
        action = "Unsubscribe"
    else:
        return {
            "success": False
        }
    
    subEmbed = discord.Embed(title=chName, description=f"{action} to the channel's:\n\n"
                                                        "1. Livestream Notifications\n2. Milestone Notifications\n3. Both\n\n"
                                                        "X. Cancel\n\n[Bypass this by setting the channel's default subscription type using `y!subdefault`]")
    
    if mode == 2:
        subEmbed.description=f"Unsubscribe to channel with subscription type:\n\n" \
                              "1. Livestream Notifications\n2. Milestone Notifications\n3. Both\n\n" \
                              "X. Cancel\n\n[Bypass this by setting the channel's default subscription type using `y!subdefault`]"

    await subMsg.edit(content=None, embed=subEmbed)

    uInput = {
        "success": False
    }

    def check(m):
        return m.content.lower() in ['1', '2', '3', 'x'] and m.author == ctx.author

    while True:
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await subMsg.delete()
            break
        else:
            if msg.content in ['1', '2', '3']:
                await msg.delete()
                if msg.content == '1':
                    uInput["subType"] = ["livestream"]
                elif msg.content == '2':
                    uInput["subType"] = ["milestone"]
                elif msg.content == '3':
                    uInput["subType"] = ["livestream", "milestone"]
                uInput["success"] = True
                break
            elif msg.content.lower() == 'x':
                await msg.delete()
                break
            else:
                await msg.delete()
    
    return uInput

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
        
        return errEmbed
    if isinstance(error, commands.CheckFailure):
        errEmbed.description = "You are missing permissions to use this bot.\n" \
                               "Ensure that you have one of these permissions for the channel/server:\n\n" \
                               " - `Administrator (Server)`\n - `Manage Webhooks (Channel/Server)`"
        
        return errEmbed
    print("An unknown error has occurred.")
    traceback.print_exception(type(error), error, error.__traceback__)
    print(error)

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

async def searchConfirm(ctx, bot, sName: str, smsg, embedDesc, accept, decline):
    sEmbed = discord.Embed(title="VTuber Search", description=embedDesc)
    sEmbed.add_field(name="Actions", value=f"Y. {accept}\nN. {decline}\nX. Cancel", inline=False)

    await smsg.edit(content=None, embed=sEmbed)

    def check(m):
        return m.content.lower() in ["y", "x"] and m.author == ctx.author
    
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
