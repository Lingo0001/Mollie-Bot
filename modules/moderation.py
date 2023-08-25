import discord
from datetime import datetime
from discord.ext import commands
from discord.ext.commands.errors import RoleNotFound
from typing import Optional
from contextlib import suppress
from utils.converters import SearchMember, SearchRole

class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument('This member has not been banned before.') from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument('This member has not been banned before.')
        return entity

class Moderation(commands.Cog, name='mod', description='Moderation Based Commands'):
    def __init__(self, bot):
        self.bot = bot
        self.db_c = bot.db_c
        self.db_conn = bot.db_conn
        self.db_c.execute('''CREATE TABLE IF NOT EXISTS 
            warnings(guild_id, user_id, mod_id, mod_type, reason, date)''')

    @commands.group(invoke_without_command=True, name='prefix', help='The bot\'s prefix in the server')
    @commands.bot_has_guild_permissions(send_messages=True)
    async def prefix(self, ctx):
        self.db_c.execute("SELECT prefix FROM guild_settings WHERE guild_id=$1",(ctx.guild.id,))
        pre = self.db_c.fetchone()
        if not pre:
            return await ctx.send('My prefix here is `.`')
        return await ctx.send(f'My prefix here is `{pre[0]}`')

    @prefix.command(name='set', aliases=['add', 'change'], help='Change the bot\'s prefix in the server')
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(send_messages=True)
    async def prefix_set(self, ctx, pre=None):
        if pre is not None:
            self.db_c.execute("UPDATE guild_settings SET prefix=$1 WHERE guild_id=$2",(pre,ctx.guild.id))
            self.db_conn.commit()
            return await ctx.send(f'Prefix set to `{pre}`')
        else:
            return await ctx.send('Please specify the new prefix')

    @commands.command(name='warn', help='Warn a member')
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(send_messages=True)
    async def warn(self, ctx, member: SearchMember, *, reason:Optional[str]="No reason provided"):
        if member == ctx.guild.owner:
            return await ctx.send('Cannot warn the owner')
        if not ctx.author == ctx.guild.owner:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send(f'Cannot warn **{member}**, check your role position')
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot warn **{member}**, check my top role position')
        else:
            with suppress(discord.HTTPException):
                await member.send(f'Warned in {ctx.guild.name} for {reason} by {ctx.author}')
            warned_at = datetime.utcnow().strftime('%D')
            mod_type = 'Warn'
            self.db_c.execute("INSERT INTO warnings VALUES($1,$2,$3,$4,$5,$6)",
                (ctx.guild.id, member.id, ctx.author.id, mod_type, reason, warned_at))
            self.db_conn.commit()
            return await ctx.send(f'Warned {member.mention}')

    @commands.command(name='kick', help='Kick a member from the server')
    @commands.has_guild_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(send_messages=True, kick_members=True)
    async def kick(self, ctx, member: SearchMember, *, reason:Optional[str]="No reason provided"):
        if member == ctx.guild.owner:
            return await ctx.send('Cannot kick the owner')
        if not ctx.author == ctx.guild.owner:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send(f'Cannot kick **{member}**, check your role position')
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot kick **{member}**, check my top role position')
        else:
            with suppress(discord.HTTPException):
                await member.send(f'Kicked from {ctx.guild.name} for {reason} by {ctx.author}')
            await member.kick(reason=f'{reason} | {ctx.author}')
            warned_at = datetime.utcnow().strftime('%D')
            mod_type = 'Kick'
            self.db_c.execute("INSERT INTO warnings VALUES($1,$2,$3,$4,$5,$6)",
                (ctx.guild.id, member.id, ctx.author.id, mod_type, reason, warned_at))
            self.db_conn.commit()             
            return await ctx.send(f'Kicked {member.mention}')

    @commands.command(name='kicks', help='Kicks a list of members from the server')
    @commands.has_guild_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(send_messages=True, kick_members=True)
    async def kicks(self, ctx, members: commands.Greedy[discord.Member], *, reason:Optional[str]="No reason provided"):
        if len(members) == 0:
            return await ctx.send_help(ctx.command)
        kickedMembers = []
        warned_at = datetime.utcnow().strftime('%D')
        mod_type = 'Kick'
        for member in members:
            if member == ctx.guild.owner:
                await ctx.send('Cannot kick the owner')
            if not ctx.author == ctx.guild.owner:
                if member.top_role >= ctx.author.top_role:
                    await ctx.send(f'Cannot kick **{member}**, check your role position')
            if member.top_role >= ctx.guild.me.top_role:
                await ctx.send(f'Cannot kick **{member}**, check my top role position')
            else:
                with suppress(discord.HTTPException):
                    await member.send(f'Kicked from {ctx.guild.name} for {reason} by {ctx.author}')
                await member.kick(reason=f'{reason} | {ctx.author}')
                kickedMembers.append(member.mention)
                self.db_c.execute("INSERT INTO warnings VALUES($1,$2,$3,$4,$5,$6)",
                (ctx.guild.id, member.id, ctx.author.id, mod_type, reason, warned_at))
                self.db_conn.commit()
        kickedMembers = ", ".join(kickedMembers)
        return await ctx.send(f'Kicked {kickedMembers}')

    @commands.command(name='ban', help='Ban a member from the server')
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(send_messages=True, ban_members=True)
    async def ban(self, ctx, member: SearchMember, *, reason:Optional[str]="No reason provided"):
        if member == ctx.guild.owner:
            return await ctx.send('Cannot ban the owner')
        if not ctx.author == ctx.guild.owner:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send(f'Cannot ban **{member}**, check your role position')
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot ban **{member}**, check my top role position')
        else:
            warned_at = datetime.utcnow().strftime('%D')
            mod_type = 'Ban'
            with suppress(discord.HTTPException):
                await member.send(f'Banned from {ctx.guild.name} for {reason} by {ctx.author}')
            await member.ban(reason=f'{reason} | {ctx.author}')
            self.db_c.execute("INSERT INTO warnings VALUES($1,$2,$3,$4,$5,$6)",
                (ctx.guild.id, member.id, ctx.author.id, mod_type, reason, warned_at))
            self.db_conn.commit()
            return await ctx.send(f'Banned {member.mention}')
    
    @commands.command(name='bans', help='Bans a list of members from the server')
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(send_messages=True, ban_members=True)
    async def bans(self, ctx, members: commands.Greedy[discord.Member], *, reason:Optional[str]="No reason provided"):
        if len(members) == 0:
            return await ctx.send_help(ctx.command)
        bannedMembers = []
        warned_at = datetime.utcnow().strftime('%D')
        mod_type = 'Ban'
        for member in members:
            if member == ctx.guild.owner:
                await ctx.send('Cannot ban the owner')
            if not ctx.author == ctx.guild.owner:
                if member.top_role >= ctx.author.top_role:
                    await ctx.send(f'Cannot ban **{member}**, check your role position')
            if member.top_role >= ctx.guild.me.top_role:
                await ctx.send(f'Cannot ban **{member}**, check my top role position')
            else:
                with suppress(discord.HTTPException):
                    await member.send(f'Banned from {ctx.guild.name} for {reason} by {ctx.author}')
                await member.ban(reason=f'{reason} | {ctx.author}')
                bannedMembers.append(member.mention)
                self.db_c.execute("INSERT INTO warnings VALUES($1,$2,$3,$4,$5,$6)",
                (ctx.guild.id, member.id, ctx.author.id, mod_type, reason, warned_at))
                self.db_conn.commit()
        bannedMembers = ", ".join(bannedMembers)
        return await ctx.send(f'Banned {bannedMembers}')

    @commands.command(name='softban', aliases=['sban'], help='Soft bans a member from the server')
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(send_messages=True, ban_members=True)
    async def softban(self, ctx, member: SearchMember, *, reason: Optional[str]="No reason provided"):
        if member == ctx.guild.owner:
            return await ctx.send('Cannot softban the owner')
        if not ctx.author == ctx.guild.owner:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send(f'Cannot softban **{member}**, check your role position')
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot softban **{member}**, check my role position')
        else:
            warned_at = datetime.utcnow().strftime('%D')
            mod_type = 'Softban'
            with suppress(discord.HTTPException):
                await member.send(f'Softbanned from {ctx.guild.name} for {reason} by {ctx.author}')
            await member.ban(reason=f'{reason} | {ctx.author}')
            await ctx.guild.unban(member, reason=f'{reason} | {ctx.author}')
            self.db_c.execute("INSERT INTO warnings VALUES($1,$2,$3,$4,$5,$6)",
                (ctx.guild.id, member.id, ctx.author.id, mod_type, reason, warned_at))
            self.db_conn.commit()
            return await ctx.send(f'Softbanned {member.mention}')

    @commands.command(name='unban', aliases=['uban'], help='Unbans a member from the server')
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(send_messages=True, ban_members=True)
    async def unban(self, ctx, member: BannedMember, *, reason: Optional[str] = "No reason provided"):
        await ctx.guild.unban(member.user, reason=reason)
        if member.reason:
            return await ctx.send(f'Unbanned {member.user} (ID: {member.user.id}), previously banned for {member.reason}.')
        else:
            return await ctx.send(f'Unbanned {member.user} (ID: {member.user.id}).')

    @commands.group(name='purge', invoke_without_command=True, help='Purge Messages', aliases=['prune'])
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_messages=True)
    async def purge(self, ctx, limit: int, *, member: SearchMember=None):
        if limit > 500:
            return await ctx.send(f'Limit is 500 messages')
        await ctx.message.delete()
        msg = []
        if not member:
            return await ctx.channel.purge(limit=limit)
        async for m in ctx.channel.history():
            if len(msg) == limit:
                break
            if m.author == member:
                msg.append(m)
        return await ctx.channel.delete_messages(msg)

    @commands.command(name='lock', help='Lock a Channel')
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_channels=True)
    async def lock(self, ctx, *, channel: discord.TextChannel=None):
        channel = channel or ctx.channel
        if ctx.guild.default_role not in channel.overwrites:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False)
            }
            await channel.edit(overwrites=overwrites)
            return await ctx.send(f'{channel.mention} is now on lockdown')
        elif channel.overwrites[ctx.guild.default_role].send_messages == True or channel.overwrites[ctx.guild.default_role].send_messages == None:
            overwrites = channel.overwrites[ctx.guild.default_role]
            overwrites.send_messages = False
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
            return await ctx.send(f'{channel.mention} is now on lockdown')
        else:
            return await ctx.send(f'{channel.mention} is already on lockdown')

    @commands.command(name='unlock', help='Unlock a Channel')
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_channels=True)
    async def unlock(self, ctx, *, channel: discord.TextChannel=None):
        channel = channel or ctx.channel
        if ctx.guild.default_role not in channel.overwrites:
            return await ctx.send(f'{channel.mention} is already unlocked')
        elif channel.overwrites[ctx.guild.default_role].send_messages == True or channel.overwrites[ctx.guild.default_role].send_messages == None:
            return await ctx.send(f'{channel.mention} is already unlocked')
        else:
            overwrites = channel.overwrites[ctx.guild.default_role]
            overwrites.send_messages = None
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
            return await ctx.send(f"{channel.mention} is now unlocked")

    @commands.group(name='role', invoke_without_command=True, help='Manage a member\'s roles')
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def role(self, ctx, user: SearchMember, *, role: SearchRole):
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles")
        if role == None:
            raise RoleNotFound(role)
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send(f'Cannot manage **{role}**, check your role position')
        if role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot manage **{role}**, check my role position')
        if role in user.roles:
            await user.remove_roles(role, reason=(f'{ctx.author.name}#{ctx.author.discriminator}'))
            return await ctx.send(f'Removed **{role}** from **{user.name}#{user.discriminator}**')
        else:
            await user.add_roles(role, reason=(f'{ctx.author.name}#{ctx.author.discriminator}'))
            return await ctx.send(f'Added **{role}** to **{user.name}#{user.discriminator}**')

    @role.command(name='addall', aliases=['aall'], help='Add a Role to Everyone')
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def role_addall(self, ctx, *, role: SearchRole):
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles")
        if role == None:
            raise RoleNotFound(role)
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send(f'Cannot manage **{role}**, check your role position')
        if role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot manage **{role}**, check my role position')
        total_members = [member for member in ctx.guild.members if role not in member.roles and not member.bot]
        msg = await ctx.send(f'⏲️ Adding **{role}** to **{len(total_members)}** Members')
        async with ctx.typing():
            for user in total_members:
                with suppress(discord.Forbidden):
                    await user.add_roles(role)
        return await msg.reply(f'✅ Added **{role}** to **{len(total_members)}** Members')

    @role.command(name='removeall', aliases=['rall'], help='Remove a Role from Everyone')
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def role_removeall(self, ctx, *, role: SearchRole):
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles")
        if role == None:
            raise RoleNotFound(role)
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send(f'Cannot manage **{role}**, check your role position')
        if role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot manage **{role}**, check my role position')
        total_members = [member for member in ctx.guild.members if role in member.roles and not member.bot]
        msg = await ctx.send(f'⏲️ Removing **{role}** from **{len(total_members)}** Members')
        async with ctx.typing():
            for user in total_members:
                with suppress(discord.Forbidden):
                    await user.remove_roles(role)
        return await msg.reply(f'✅ Removed **{role}** from **{len(total_members)}** Members')

    @role.command(name='create', help='Create a Role')
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def role_create(self, ctx, colour: discord.Colour, *, rolename):
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles")
        role = await ctx.guild.create_role(colour=colour, name=rolename)
        if str(role.colour) == "#000000":
            colour = "default"
            color = discord.Colour.default()
        else:
            colour = str(role.colour).upper()
            color = role.color
        em = discord.Embed(colour=color)
        em.set_author(name=f"Name: {role.name}\nRole ID: {role.id}")
        em.add_field(name="Mentionable", value=role.mentionable, inline=True)
        em.add_field(name="Hoist", value=role.hoist, inline=False)
        em.add_field(name="Position", value=role.position, inline=False)
        em.add_field(name="Colour", value=colour, inline=False)
        return await ctx.send(f'**{role.mention}** Created!', embed=em)

    @role.command(name='delete', help='Delete a Role')
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def role_delete(self, ctx, *, role: SearchRole):
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles")
        if role == None:
            raise RoleNotFound(role)
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send(f'Cannot delete **{role}**, check your role position')
        if role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot delete **{role}**, check my role position')
        else:
            await role.delete()
            return await ctx.send(f'Deleted **{role}**')

    @role.group(name='edit', invoke_without_command=True, help='Edit a Role base command')
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def role_edit(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @role_edit.command(name='colour', aliases=['color'], help='Edit a Role\'s Colour')
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def role_edit_colour(self, ctx, role: SearchRole, *, colour: discord.Colour):
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles")
        if role == None:
            raise RoleNotFound(role)
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send(f'Cannot edit the colour of **{role}**, check your role position')
        if role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot edit the colour of  **{role}**, check my role position')
        else:
            await role.edit(colour=colour)
            return await ctx.send(f'**{role}\'s** Colour changed to **{colour}**')

    @role_edit.command(name='name', help='Edit a Role\'s Name')
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def role_edit_name(self, ctx, role: SearchRole, *, newrolename):
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles")
        rolename = role.name
        if role == None:
            raise RoleNotFound(role)
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send(f'Cannot edit the name of **{role}**, check your role position')
        if role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot edit the name of **{role}**, check my role position')
        else:
            await role.edit(name=newrolename)
            return await ctx.send(f'Role **{rolename}\'s** Name changed to **{newrolename}**')

    @commands.command(name='muterole', help='Set a Muted role', aliases=['mutedrole'])
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def mutedrole(self, ctx, *, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            return await ctx.send('Cannot manage this role, check my top role position')
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send(f'Cannot manage **{role}**, check your role position')
        if role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot manage **{role}**, check my role position')
        self.db_c.execute("UPDATE guild_settings SET muterole=$1 WHERE guild_id=$2", (role.id, ctx.guild.id))
        self.db_conn.commit()
        return await ctx.send(f'Muted role set as {role.mention}')

    async def search_mute(self, ctx):
        self.db_c.execute("SELECT muterole FROM guild_settings WHERE guild_id=$1",(ctx.guild.id,))
        result = self.db_c.fetchone()
        if result is None:
            muteRole = discord.utils.find(lambda r: r.name.lower() == 'muted', ctx.guild.roles)
            if muteRole is None:
                muteRole = await ctx.guild.create_role(name='Muted', reason='Bot Muted Role')
                self.db_c.execute("UPDATE guild_settings SET muterole=$1 WHERE guild_id=$2", 
                (muteRole.id, ctx.guild.id))
                self.db_conn.commit()
        else:
            muteRole = result[0]
            muteRole = ctx.guild.get_role(muteRole)
            if muteRole is None:
                muteRole = discord.utils.find(lambda r: r.name.lower() == 'muted', ctx.guild.roles)
                if muteRole is None:
                    muteRole = await ctx.guild.create_role(name='Muted', reason='Bot Muted Role')
                    self.db_c.execute("UPDATE guild_settings SET muterole=$1 WHERE guild_id=$2", 
                    (muteRole.id, ctx.guild.id))
                    self.db_conn.commit()
        return muteRole

    @commands.command(name='mute', help='Mute a member')
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def mute(self, ctx, member: SearchMember, *, reason: Optional[str] = "No reason provided"):
        muteRole = await self.search_mute(ctx)
        if member == ctx.guild.owner:
            return await ctx.send(f'Cannot mute the owner')
        if muteRole in member.roles:
            return await ctx.send(f'**{member}** is already muted')
        if not ctx.author == ctx.guild.owner:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send(f'Cannot mute **{member}**, check your role position')
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot mute **{member}**, check my role position')
        else:
            warned_at = datetime.utcnow().strftime('%D')
            mod_type = 'Mute'
            await member.add_roles(muteRole)
            self.db_c.execute("INSERT INTO warnings VALUES($1,$2,$3,$4,$5,$6)",
                (ctx.guild.id, member.id, ctx.author.id, mod_type, reason, warned_at))
            self.db_conn.commit()
            await ctx.send(f'Muted {member.mention}')
            with suppress(discord.HTTPException):
                return await member.send(f'You were muted in {ctx.guild.name} for {reason}')

    @commands.command(name='unmute', help='Unmute a member')
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(send_messages=True, manage_roles=True)
    async def unmute(self, ctx, member: SearchMember, *, reason: Optional[str] = "No reason provided"):
        muteRole = await self.search_mute(ctx)
        if member == ctx.guild.owner:
            return await ctx.send(f'Cannot unmute the owner')
        if muteRole not in member.roles:
            return await ctx.send(f'**{member}** is already unmuted')
        if not ctx.author == ctx.guild.owner:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send(f'Cannot unmute **{member}**, check your role position')
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(f'Cannot unmute **{member}**, check my role position')
        else:
            warned_at = datetime.utcnow().strftime('%D')
            mod_type = 'Unmute'
            await member.remove_roles(muteRole)
            self.db_c.execute("INSERT INTO warnings VALUES($1,$2,$3,$4,$5,$6)",
                (ctx.guild.id, member.id, ctx.author.id, mod_type, reason, warned_at))
            self.db_conn.commit()
            await ctx.send(f'Unmuted {member.mention}')
            with suppress(discord.HTTPException):
                return await member.send(f'You were unmuted in {ctx.guild.name} for {reason}')

async def setup(bot):
    await bot.add_cog(Moderation(bot))