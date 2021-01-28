from itertools import islice

def chunks(data, SIZE=10000):
    it = iter(data)
    for i in range(0, len(data), SIZE):
        yield {k:data[k] for k in islice(it, SIZE)}

def creatorCheck(ctx):
    return ctx.author.id == 256009740239241216

def subPerms(ctx):
    userPerms = ctx.channel.permissions_for(ctx.author)
    return userPerms.administrator or userPerms.manage_webhooks or ctx.guild.owner_id == ctx.author.id