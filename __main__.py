import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio

import re
import os
import json

import math
import datetime
from random import choice
from hangul import *

from pytz import timezone

KST = timezone('Asia/Seoul')

try:
    from secret import set_secret
    set_secret()
except ModuleNotFoundError:
    pass


intents = discord.Intents.all()
bot = commands.Bot(command_prefix='?', intents=intents)
bot.kenwords = {}
bot.rwa = []
bot.reacting = None
bot.late = False
bot.member_list = None


def get_custom_emoji_embed(emoji_name: str):
    emoji = discord.utils.get(bot.emojis, name=emoji_name)
    embed = discord.Embed()
    embed.set_image(url=emoji.url)
    embed.set_footer(text=f':{emoji.name}:')
    return embed


def get_custom_sticker_embed(sticker: str):
    embed = discord.Embed()
    embed.set_image(url=sticker.url)
    embed.set_footer(text=f'{sticker.name}')
    return embed


def get_member_list_embed(members: list, page: int, max_page: int):
    embed = discord.Embed(description='```\n'+'\n\n'.join(members)+'\n```')
    embed.set_footer(text=f'{page} / {max_page}')
    return embed


def fetch_kenwords():
    with open('./kenwords.json', mode='r', encoding='utf-8') as fp:
        bot.kenwords = json.load(fp)


def kenken_called(message: str):
    count = 0
    for ken in bot.kenwords['ken']:
        count += message.count(ken)
    if count < 2:
        count = 0
    if not count and any(word in message.upper()
                         for word in ('KENKEN', '켄켄', str(bot.user.id), bot.user.display_name)):
        count = 2
    return count


class EmbedPagerView(View):
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
async def on_fast_message(message):
    if bot.reacting is None:
        bot.late = False
        return
    if bot.reacting.channel is message.channel:
        bot.late = True


@bot.listen('on_message')
async def on_name_called(message):
    if message.author == bot.user:
        return
    called = kenken_called(message.content)
    if called < 2:
        return
    positions = []
    for pos, character in enumerate(message.content.replace(' ', '')):
        if character in bot.kenwords['ken']:
            positions.append(pos)
    min_dist = 2000
    for p1, p2 in zip(positions, positions[1:]):
        dist = p2 - p1
        if dist < min_dist:
            min_dist = p2 - p1
    bot.reacting = message
    async with message.channel.typing():
        await asyncio.sleep(min(min_dist / 5, 5))
    if min_dist >= 30:
        bot.reacting = None
        return
    if any(bad_word in ''.join(e for e in message.content if e.isalnum())
           for bad_word in bot.kenwords['bad_word']):
        await message.channel.send('ㅜㅠ',
                                   reference=message if bot.late else None)
    elif any(greet in message.content for greet in bot.kenwords['greet']):
        await message.channel.send(choice(bot.kenwords['greet_answer']),
                                   reference=message if bot.late else None)
    elif called > 2:
        await message.channel.send(''.join([choice(bot.rwa) for _ in range(called)])[:1997]
                                   + ''.join([choice(tuple('!?.'))
                                             for _ in range(3)]),
                                   reference=message if bot.late else None)
    else:
        await message.channel.send(choice(bot.kenwords['answer']),
                                   reference=message if bot.late else None)
    bot.reacting = None


@bot.listen('on_message')
async def on_emoji_message(message):
    if message.author == bot.user:
        return
    emojis = list(re.compile(r'<:[a-zA-Z_0-9]+:\d+>').findall(message.content))
    if emojis:
        embeds = [get_custom_emoji_embed(emoji.split(':')[1])
                  for emoji in emojis]
        view = EmbedPagerView(embeds) if len(embeds) > 1 else None
        await message.channel.send(embed=embeds[0], view=view, delete_after=30,
                                   reference=message if bot.late else None)


@bot.listen('on_message')
async def on_sticker_message(message):
    if message.author == bot.user:
        return
    stickers = message.stickers
    if stickers:
        embeds = [get_custom_sticker_embed(sticker)
                  for sticker in stickers]
        view = EmbedPagerView(embeds) if len(embeds) > 1 else None
        await message.channel.send(embed=embeds[0], view=view, delete_after=30,
                                   reference=message if bot.late else None)


@bot.listen('on_message')
async def on_bad_word(message):
    if message.author == bot.user:
        return
    if any(bad_word in ''.join(e for e in message.content if e.isalnum())
           for bad_word in bot.kenwords['bad_word']):
        await message.add_reaction('😱')


@bot.command(name='멤버')
async def members(ctx):
    if ctx.guild is None:
        return
    members = sorted(ctx.guild.members, key=lambda m: m.joined_at)
    members = [
        discord.utils.escape_markdown(
            "{:02d}".format(i+1) + '. '
            + member.display_name
            + ('(' + member.name + ')' if member.nick else '')
            + '\n  - '
            + member.joined_at
            .astimezone(KST).strftime('%Y-%m-%d %H:%M:%S')
            + ' 가입')
        for (i, member) in enumerate(members)]
    embeds = [
        get_member_list_embed(
            members[i:i+10], i // 10 + 1, math.ceil(len(members) / 10))
        for i in range(0, len(members), 10)]
    view = EmbedPagerView(embeds) if len(embeds) > 1 else None
    member_list = await ctx.channel.send(embed=embeds[0], view=view, delete_after=60,
                                         reference=ctx.message if bot.late else None)
    if bot.member_list is not None:
        await bot.member_list.delete()
    bot.member_list = member_list

fetch_kenwords()
for initial in ('ㅁ', 'ㅇ', 'ㄹ', 'ㄴ'):
    for final in ('ㅁ', 'ㅇ', 'ㄴ', None):
        for medial in map(str, CHAR_MEDIALS):
            bot.rwa.append(join_jamos_char(initial, medial, final))


bot_token = os.environ['BOT_TOKEN']

bot.run(bot_token)
