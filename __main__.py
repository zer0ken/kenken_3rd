import discord
from discord.ext import commands
from discord.ui import Button, View

import re
import os
import random

from boto.s3.connection import S3Connection

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='?', intents=intents)


def get_custom_emoji_embed(emoji_name: str):
    print(emoji_name, bot.emojis)
    emoji = discord.utils.get(bot.emojis, name=emoji_name)
    embed = discord.Embed()
    embed.set_image(url=emoji.url)
    embed.set_footer(text=f':{emoji.name}:')
    return embed


class EmojiView(View):
    def __init__(self, embeds):
        super().__init__()
        self.embeds = embeds

    @discord.ui.button(label="이전", style=discord.ButtonStyle.secondary, emoji='⏪')
    async def prev_button_callback(self, interaction, button):
        self.embeds = [self.embeds[-1]] + self.embeds[:-1]
        await interaction.response.edit_message(embed=self.embeds[0], view=self)

    @discord.ui.button(label="다음", style=discord.ButtonStyle.primary, emoji='⏩')
    async def next_button_callback(self, interaction, button):
        self.embeds = self.embeds[1:] + [self.embeds[0]]
        await interaction.response.edit_message(embed=self.embeds[0], view=self)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


@bot.listen('on_message')
async def on_name_called(message):
    if message.author == bot.user:
        return
    if '켄켄' not in message.content and bot.user not in message.mentions:
        return 
    answer = [
        '불럿어?',
        '불ㄹ엇어?',
        '불란서?',
        'ㅁ웅',
        '인ㅇ!',
        '켄켄이다!',
        'yee~'
    ]
    await message.channel.send(random.choice(answer))


@bot.listen('on_message')
async def on_emoji_message(message):
    if message.author == bot.user:
        return

    emojis = list(set(re.compile(r'<:[a-zA-Z_0-9]+:\d+>').findall(message.content)))
    if emojis:
        embeds = [get_custom_emoji_embed(emoji.split(':')[1]) for emoji in emojis]
        view = EmojiView(embeds) if len(embeds) > 1 else None
        await message.channel.send(embed=embeds[0], reference=message, view=view, delete_after=30)


s3 = S3Connection(os.environ['S3_KEY'], os.environ['S3_SECRET'])
bot_token = os.environ['BOT_TOKEN']
bot.run(bot_token)