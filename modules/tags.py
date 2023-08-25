import discord
import datetime
from discord.ext import commands
from utils import pages
from utils.converters import SearchMember

class Tags(commands.Cog, name='tags', description='Tag Commands'):
    def __init__(self, bot):
        self.bot = bot
        self.colour = bot.colour
        self.db_conn = bot.db_conn
        self.db_c = bot.db_c
        self.db_c.execute('''CREATE TABLE IF NOT EXISTS tags(guild_id, author_id, uses, name, content, creation)''')

    def clean_tag_content(self, content):
        return content.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')
    
    def verify_lookup(self, lookup):
        if '@everyone' in lookup or '@here' in lookup:
            raise RuntimeError('That tag is using blocked words.')

        if not lookup:
            raise RuntimeError('You need to actually pass in a tag name.')

        if len(lookup) > 50:
            raise RuntimeError('Tag name is a maximum of 50 characters.')

    async def do_tag_stuff(self, ctx, name):
        lookup = name.lower()
        if not ctx.guild:
            raise commands.NoPrivateMessage
        else:
            self.db_c.execute("SELECT content FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
            t = self.db_c.fetchone()
            if t is None:
                return await ctx.send(f'Tag **{lookup}** doesn\'t exist')
            await ctx.send(t[0])
            self.db_c.execute("UPDATE tags SET uses = uses + 1 WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
            self.db_conn.commit()
        
    @commands.group(name='tag', invoke_without_command=True, help='Look for a tag')
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def tag(self, ctx, name: str):
        return await self.do_tag_stuff(ctx, name)

    @tag.error
    async def tag_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send('You need to mention the tag name')
    
    @tag.command(name='get', hidden=True, help='Get a tag')
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def tag_get(self, ctx, name: str):
        return await self.do_tag_stuff(ctx, name)

    @tag.command(name='create', help='Create a tag', aliases=['add', '+'])
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def tag_create(self, ctx, name: str, *, content: str):
        if ctx.message.mentions:
            return await ctx.send('Tags can\'t include mentions')
        content = self.clean_tag_content(content)
        lookup = name.lower().strip()
        try:
            self.verify_lookup(lookup)
        except RuntimeError as e:
            return await ctx.send('A RunTimeError has occurred, try again')
        self.db_c.execute("SELECT name FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
        result = self.db_c.fetchone()
        if result:
            return await ctx.send('A tag with that name already exists')
        self.db_c.execute("INSERT INTO tags VALUES($1,$2,$3,$4,$5,$6)",
            (ctx.guild.id, ctx.author.id, 0, name, content, datetime.datetime.utcnow().strftime("%d %b %Y %H:%M")))
        self.db_conn.commit()
        return await ctx.send(f'Created tag **{name}**')

    @tag.command(name='edit', help='Edit a tag', aliases=['update'])
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def tag_edit(self, ctx, name: str, *, content: str):
        if ctx.message.mentions:
            return await ctx.send('Tags can\'t include mentions')
        content = self.clean_tag_content(content)
        lookup = name.lower().strip()
        try:
            self.verify_lookup(lookup)
        except RuntimeError as e:
            return await ctx.send('A RunTimeError has occurred, try again')
        self.db_c.execute("SELECT name FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
        result = self.db_c.fetchone()
        if result is None:
            return await ctx.send('A tag with that name doesn\'t exist')
        self.db_c.execute("UPDATE tags SET content=$1 WHERE name=$2 AND guild_id=$3",(content, lookup, ctx.guild.id))
        self.db_conn.commit()
        return await ctx.send(f'Edited tag **{name}**')

    @tag.command(name='append', help='Add something to an existing tag. A newline will be inserted.', aliases=['+=', 'add'])
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def tag_append(self, ctx, name: str, *, content: str):
        if ctx.message.mentions:
            return await ctx.send('Tags can\'t include mentions')
        content = self.clean_tag_content(content)
        lookup = name.lower().strip()
        try:
            self.verify_lookup(lookup)
        except RuntimeError as e:
            return await ctx.send('A RunTimeError has occurred, try again')
        self.db_c.execute("SELECT name FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
        result = self.db_c.fetchone()
        if result is None:
            return await ctx.send('A tag with that name doesn\'t exist')
        self.db_c.execute("SELECT content FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
        content_result = self.db_c.fetchone()
        appended_tag = content_result[0] + '\n{}'.format(content)
        if len(appended_tag) >= 2000:
                len_orig = len(content_result[0])
                return await ctx.send(f'That would make the tag too long (2000 characters), the original tag\'s length is {len_orig} characters')
        self.db_c.execute("UPDATE tags SET content=$1 WHERE name=$2 AND guild_id=$3", (appended_tag, lookup, ctx.guild.id))
        self.db_conn.commit()
        return await ctx.send(f'Appended tag **{name}**')
    
    @tag.command(name='delete', aliases=['-', 'remove', 'del'], help='Delete a tag')
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def tag_delete(self, ctx, *, name: str):
        lookup = name.lower()
        self.db_c.execute("SELECT name FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
        result = self.db_c.fetchone()
        if result is None:
            return await ctx.send('A tag with that name doesn\'t exist')
        self.db_c.execute("DELETE FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
        self.db_conn.commit()
        return await ctx.send(f'Deleted tag **{name}**')

    @tag.command(name='info', help='Displays information about a tag')
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def tag_info(self, ctx, name: str):
        lookup = name.lower()
        self.db_c.execute("SELECT name FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
        result = self.db_c.fetchone()
        if result is None:
            return await ctx.send('A tag with that name doesn\'t exist')
        self.db_c.execute("SELECT * FROM tags WHERE name=$1 AND guild_id=$2", (lookup, ctx.guild.id))
        result = self.db_c.fetchone()
        owner_id = result[1]
        uses = result[2]
        date = result[5]
        embed = discord.Embed(
            colour=self.colour,
            title=name
        )
        owner = ctx.guild.get_member(owner_id)
        if not owner:
            owner = self.bot.get_user(owner_id)
        embed.add_field(name='Owner', value=owner.mention, inline=False)
        embed.add_field(name='Uses', value=round(uses), inline=False)
        self.db_c.execute("SELECT uses FROM tags WHERE guild_id=$1", (ctx.guild.id,))
        rank_result = self.db_c.fetchall()
        rank = sorted([x[0] for x in rank_result], reverse=True).index(uses) + 1
        embed.add_field(name='Rank', value=rank, inline=False)
        embed.set_footer(text=f'Tag created on {date}')
        return await ctx.send(embed=embed)

    async def tag_list_stuff(self, ctx, tags):
        tags = [x[0] for x in tags]
        if sum(len(t) for t in tags) < 1900:
            d = ', '.join(tags)
            try:
                return await ctx.author.send(d)
            except:
                return await ctx.send(d)
        else:
            tempmessage = []
            finalmessage = []
            for tag in tags:
                if len(', '.join(tempmessage)) < 1800:
                    tempmessage.append(tag)
                else:
                    formatted_tempmessage = ', '.join(tempmessage)
                    finalmessage.append(formatted_tempmessage)
                    tempmessage = []
            finalmessage.append(', '.join(tempmessage))
            for x in finalmessage:
                if x != "":
                    try:
                        return await ctx.author.send(x)
                    except:
                        return await ctx.send(x)

    @tag.command(name='mine', help='Shows all tags a member has created')
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def tag_mine(self, ctx, *, user: SearchMember=None):
        user = user or ctx.author
        self.db_c.execute("SELECT name FROM tags WHERE guild_id=$1 AND author_id=$2 ORDER BY name ASC", (ctx.guild.id, user.id))
        tags = self.db_c.fetchall()
        if len(tags) == 0:
            return await ctx.send('This user has created no tags')
        return await self.tag_list_stuff(ctx, tags)

    @tag.command(name='list', help='Shows you the names of all tags')
    @commands.bot_has_guild_permissions(send_messages=True)
    async def tag_list(self, ctx):
        self.db_c.execute("SELECT name FROM tags WHERE guild_id=$1 AND LENGTH(name) > 2 ORDER BY name ASC", (ctx.guild.id,))
        tags = self.db_c.fetchall()
        if len(tags) == 0:
            return await ctx.send('This server has created no tags')
        return await self.tag_list_stuff(ctx, tags)

    @commands.command(name='tags', help='Shows you the names of all tags', aliases=['taglist'])
    @commands.bot_has_guild_permissions(send_messages=True)
    async def tags(self, ctx):
        self.db_c.execute("SELECT name FROM tags WHERE guild_id=$1 AND LENGTH(name) > 2 ORDER BY name ASC", (ctx.guild.id,))
        tags = self.db_c.fetchall()
        if len(tags) == 0:
            return await ctx.send('This server has created no tags')
        return await self.tag_list_stuff(ctx, tags)

    @tag.command(name='random', help='Show a random tag')
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def tag_random(self, ctx):
        self.db_c.execute("SELECT name FROM tags WHERE guild_id=$1 ORDER BY RANDOM() LIMIT 1", (ctx.guild.id,))
        tag = self.db_c.fetchone()
        if tag is None:
            return await ctx.send('This server has created no tags')
        self.db_c.execute("UPDATE tags SET uses = uses + 1 WHERE guild_id=$1 AND name=$2", (ctx.guild.id, tag[0]))
        self.db_conn.commit()
        return await ctx.send(tag[0])

    @tag.command(name='search', help='Search for a tag')
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True, add_reactions=True)
    async def tag_search(self, ctx, *, query: str):
        query = query.lower()
        if len(query) < 2:
            return await ctx.send('Tag name query must be 2 characters or more')
        self.db_c.execute("SELECT name FROM tags WHERE guild_id=$1 AND LENGTH(name) > 2 ORDER BY uses DESC", (ctx.guild.id,))
        tags = self.db_c.fetchall()
        if len(tags) == 0:
            return await ctx.send('This server has created no tags')
        results = [x[0] for x in tags]
        final_list = [x for x in results if query in x]
        if len(final_list) == 0:
            return await ctx.send('No tags found')
        embed = discord.Embed(
            colour=self.colour,
            title='Search Results:'
        )
        if ctx.author.avatar:
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        else:
            embed.set_author(name=ctx.author.display_name)
        embed.set_footer(text=f'{len(final_list)} results')
        rows = [word for word in final_list]
        return await pages.send_as_pages(ctx, embed, rows)

async def setup(bot):
    await bot.add_cog(Tags(bot))