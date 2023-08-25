import discord
import random
from discord.ext import commands

class Fun(commands.Cog, name='fun', description='Fun Commands'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='eightball', help='Ask the magic 8 ball a question', aliases=['8ball', 'magic8ball', 'magicball'])
    @commands.bot_has_guild_permissions(send_messages=True)
    async def eightball(self, ctx, *, question):
        responses = ["It is certain.",
                    "It is decidedly so.",
                    "Without a doubt.",
                    "Yes – definitely.",
                    "You may rely on it.",
                    "As I see it, yes.",
                    "Most likely.",
                    "Outlook good.",
                    "Yes.",
                    "Signs point to yes.",
                    "Reply hazy, try again.",
                    "Ask again later.",
                    "Better not tell you now.",
                    "Cannot predict now.",
                    "Concentrate and ask again.",
                    "Don't count on it.",
                    "My reply is no.",
                    "My sources say no.",
                    "Outlook not so good.", 
                    "Very doubtful."]
        return await ctx.reply(f'🎱 {random.choice(responses)}')

    
    @commands.command(name='choose', help='Choose from given options', usage='<option1> or <option2> or...')
    @commands.bot_has_guild_permissions(send_messages=True)
    async def choose(self, ctx, *, choices):
        choices = choices.split(' or ')
        if len(choices) < 2:
            return await ctx.reply('Give me at least 2 options to choose from (separate choices with **or**)')
        choice = random.choice(choices).strip()
        return await ctx.reply(f'I choose **{choice}**')

    @commands.command(name='flip', help='Flip a coin')
    @commands.bot_has_guild_permissions(send_messages=True)
    async def flip(self, ctx, coins:int=1):
        if coins > 10:
            return await ctx.reply('Max amount of flips is 10')
        if coins < 1:
            return await ctx.reply('Min amount of flips is 1')
        answers = []
        for i in range(coins):
            answers.append(random.choice(('Heads!', 'Tails!')))
        answers = '\n'.join(answers)
        return await ctx.reply(answers)

    @commands.command(name='echo', help='Makes the bot say something in the specified channel')
    @commands.bot_has_guild_permissions(send_messages=True, add_reactions=True)
    async def echo(self, ctx, destination: discord.TextChannel=None, *, msg: str):
        if not destination.permissions_for(ctx.author).send_messages or not destination.permissions_for(ctx.guild.me).send_messages:
            return await ctx.message.add_reaction("⛔")
        msg = msg.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')
        destination = destination or ctx.author
        await destination.send(msg)
        return await ctx.message.add_reaction("✅")

    @commands.command(name='clyde', help='Make Clyde say something')
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def clyde(self, ctx, *, message):
        if len(message) > 90:
            return await ctx.reply('Message too long, max characters is 90')
        async with ctx.channel.typing():
            async with self.bot.session.get(f'https://nekobot.xyz/api/imagegen?type=clyde&text={message}') as r:
                data = await r.json()
        embed = discord.Embed(
            colour=self.bot.colour
        )
        embed.set_image(url=data['message'])
        return await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Fun(bot))