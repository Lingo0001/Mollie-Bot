import discord
import re
from discord.ext import commands
from discord.ext.commands.errors import NoPrivateMessage, RoleNotFound, MemberNotFound

class SearchMember(commands.MemberConverter):
    """A Member Converter to replace `discord.Member`
    so that users don't have to enter a Member's name fully.
    For example a user can input 'Josh' for 'Josh Stevens'.
    Also works for Nicknames.
    Is not case sensitive.
    """
    async def query_member_named(self, guild, argument):
        cache = guild._state.member_cache_flags.joined
        members = await guild.query_members(argument, limit=100, cache=cache)
        if len(argument) > 5 and argument[-5] == '#':
            username, _, discriminator = argument.rpartition('#')
            members = await guild.query_members(username, limit=100, cache=cache)
            return discord.utils.get(members, name=username, discriminator=discriminator)
        else:
            for member in members:
                if argument.lower() in member.name.lower():
                    return member
                elif argument.lower() in member.display_name.lower():
                    return member
                else:
                    raise MemberNotFound(argument)

class SearchRole(commands.RoleConverter):
    """A Role Converter to replace 'discord.Role'
    so that users don't have to enter a role's name fully.
    For example a user can input 'Mod' for 'Moderator'.
    Is not case sensitive.
    """
    async def convert(self, ctx, argument):
        guild = ctx.guild
        if not guild:
            raise NoPrivateMessage()

        match = self._get_id_match(argument.lower()) or re.match(r'<@&([0-9]+)>$', argument.lower())
        if match:
            result = guild.get_role(int(match.group(1)))
        else:
            result = discord.utils.find(lambda r: r.name.lower() == argument.lower(), guild._roles.values())

        if result is None:
            roles = guild._roles.values()
            for role in roles:
                if argument.lower() in role.name.lower():
                    result = role
                    if result is None:
                        raise RoleNotFound(argument)
        return result