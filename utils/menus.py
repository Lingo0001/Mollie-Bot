import discord
from discord.ext import menus

class MyMenu(menus.Menu):
    def __init__(self, modules):
        self.modules = modules
        super().__init__(timeout=60)

    async def send_initial_message(self, ctx, channel):
        self.modulenumber=0
        return await channel.send(embed=self.modules[self.modulenumber])

    @menus.button('\U00002b05')
    async def previous(self, payload):
        if self.modulenumber == 0:
            self.modulenumber=len(self.modules) - 1
        else:
            self.modulenumber -= 1
        await self.message.edit(embed=self.modules[self.modulenumber])

    @menus.button('\U000023f9')
    async def cancel(self, payload):
        await self.message.clear_reactions()
        self.stop()

    @menus.button('\U000027a1')
    async def next(self, payload):
        if self.modulenumber == len(self.modules) - 1:
            self.modulenumber=0
        else:
            self.modulenumber += 1
        await self.message.edit(embed=self.modules[self.modulenumber])

    @menus.button('\N{WASTEBASKET}')
    async def delete(self, payload):
        await self.message.delete()