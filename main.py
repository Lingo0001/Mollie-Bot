# Discord
import discord
from discord.ext import commands

# Logging
import logging
import traceback
import sys

# Storing in SQLITE3 as Bot not in massive number of servers
import sqlite3
import asyncio
import contextlib
from aiohttp import ClientSession

# Mine
# from utils.help import MyHelp
# from secrets import config

# TOKEN = config['token']
# BOT_ID = config['bot_id']
# OWNER_ID = config['owner_id']

MODULES = [
    'modules.fun',
    'modules.moderation',
    'modules.tags'
]

DEFAULT_PREFIX = '.'

db_conn = sqlite3.connect('main.sqlite')
db_c = db_conn.cursor()

def get_prefix(bot,msg):
    db_c.execute("SELECT prefix FROM guild_settings WHERE guild_id=?", (msg.guild.id,))
    prefix_result = db_c.fetchone()
    if prefix_result is None:
        db_c.execute("INSERT INTO guild_settings(guild_id, prefix) VALUES(?,?)", (msg.guild.id, DEFAULT_PREFIX))
        db_conn.commit()
        prefix = DEFAULT_PREFIX
    else:
        prefix = prefix_result[0]
    return commands.when_mentioned_or(prefix)(bot, msg)

async def load_modules(bot):
    for exe in MODULES:
        try:
            await bot.load_extension(exe)
            print(f'Loaded {exe}')
        except:
            print(f'Failed to load module {exe}.', file=sys.stderr)
            traceback.print_exc()

async def run():
    db_c.execute("CREATE TABLE IF NOT EXISTS guild_settings(guild_id, prefix)")
    async with ClientSession() as session:
        bot = Mollie(session=session, db_c=db_c, db_conn=db_conn)
        try:
            await load_modules(bot)
            # await bot.start(TOKEN)
        except KeyboardInterrupt:
            await bot.close()
            await bot.session.close()

class Mollie(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=get_prefix,
            description='Mollie Bot, pretty cool',
            case_insensitive=True,
            strip_after_prefix=True,
            # help_command=MyHelp(self.colour),
            intents=discord.Intents.all(),
            allowed_mentions=discord.AllowedMentions(
                roles=False,
                everyone=False,
                users=False,
                replied_user=False
            ),
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name='purring'
            )
        )
        # self.owner_id=OWNER_ID
        # self.bot_id=BOT_ID
        self.session=kwargs.pop('session')
        self.db_c=kwargs.pop('db_c')
        self.db_conn=kwargs.pop('db_conn')

    @property
    def colour(self):
        # Server Booster Colour
        return 0xF47FFF
    
    async def on_ready(self):
        self.uptime = discord.utils.utcnow()
        print(f'Logged in as: {self.user}')
        print(f'Can see {len(self.guilds)} Guilds and {len(self.users)} Users')

    async def on_command_error(self, ctx, error):
        # I believe the beginning part of this is from Rapptz's Documentation
        # Could be wrong..
        if hasattr(ctx.command, 'on_error'):
            return
        
        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.NotOwner, commands.DisabledCommand)

        if isinstance(error, ignored):
            with contextlib.suppress(discord.Forbidden):
                return await ctx.message.add_reaction('🚫')
            
        if isinstance(error, commands.CommandNotFound):
            
            lookup = ctx.invoked_with.lower()
            if not ctx.guild:
                raise commands.NoPrivateMessage
            else:
                self.db_c.execute("SELECT content FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
                t = self.db_c.fetchone()
                if t is None:
                    return
                await ctx.send(t[0])
                self.db_c.execute("UPDATE tags SET uses = uses + 1 WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
                self.db_conn.commit()

        elif isinstance(error, commands.MissingPermissions):
            error = error.missing_perms[0].replace('_', ' ')
            return await ctx.send(f'You need **{error}** permissions to use: `{ctx.invoked_with}`')

        elif isinstance(error, commands.BotMissingPermissions):
            error = error.missing_perms[0].replace('_', ' ')
            return await ctx.send(f'Bot needs **{error}** permissions to use: `{ctx.invoked_with}`')

        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send_help(ctx.command)

        elif isinstance(error, commands.NoPrivateMessage):
            with contextlib.suppress(discord.HTTPException):
                return await ctx.author.send(f'**{ctx.command}** cannot be used in DMs')
            
        elif isinstance(error, commands.CommandOnCooldown):
            time = error.retry_after
            if time < 60:
                return await ctx.send(f'Try in **{round(time)} seconds**')
            else:
                time = round(time/60)
                return await ctx.send(f'Try in **{time} minutes**')
            
        elif isinstance(error, commands.BadArgument):
            return await ctx.send(embed=discord.Embed(colour=discord.Colour.dark_grey(),description=f'{error}'))
        
        else:
            print(f'Ignoring execption in command {ctx.command}:', file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            return await ctx.send(f"Unexpected error, alerted dev. `{ctx.prefix}support` if it carries on.")
        
    async def close(self):
        await super().close()
        await self.session.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(run())