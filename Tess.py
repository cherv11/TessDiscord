import discord
from discord.ext import commands, tasks
import asyncio
import os
import time
import math
import random
from collections import defaultdict
import json
import requests
import sqlite3
import datetime

DIR = os.path.dirname(__file__)
db = sqlite3.connect(os.path.join(DIR, "Tess.db"))
SQL = db.cursor()

tessguildid = 884945081138823198

logchannel = None
hwchannel = None
hwchannelid = 884945553480359969
botcage = 823312775468023858

admins = [891966113473249282, 262288342035595268] # бот, Дима
dima = None
dimaid = 262288342035595268

# colors
raincolors = [0xff0000, 0x8b0000, 0xcd5c5c, 0xff1493,
              0xff4500, 0xffa000, 0xffd700, 0xffff00,
              0xee82ee, 0x9400d3, 0x8b008b, 0x4b0082,
              0xccff00, 0x00ff00, 0x00ff7f, 0x006400,
              0x08e8de, 0x00bfff, 0x2c75ff, 0x00008b,
              0xb8860b, 0xd2691e, 0x8b4513, 0x808000, 0xf0e68c, 0xffd1b8]

# experience
congrats = 0
e_savetime = 120
e_onlinetime = 5
e_online = 50
e_message = 250
e_picture = 300
ek_congrats = 1

client = discord.Client()
prefix = '*'
bot = commands.Bot(command_prefix=prefix, intents=discord.Intents.all())
bot.remove_command("help")
t = (2021, 10, 6, 18, 55, 00, 3, 0, 0)
lessons = [10**10]+[time.mktime(t)+i*604800 for i in range(27)]
expd = defaultdict(dict)


def postfix(v, ps, rv=True):
    if v % 10 in [0, 5, 6, 7, 8, 9] or v % 100 in [11, 12, 13, 14]:
        p = ps[2]
    elif v % 10 == 1:
        p = ps[0]
    else:
        p = ps[1]
    if rv: return f'{v} {p}'
    return p


def tesort(l):
    a = [v for v in l]
    for i in range(len(a) - 1):
        for j in range(len(a) - i - 1):
            if a[j].exp < a[j + 1].exp:
                a[j], a[j + 1] = a[j + 1], a[j]
    return a


def levelmode(x, mode=0):
    if mode == 0:
        return 2700 * x ** 1.552700
    elif mode == 1:
        return 15 * x ** 2.5
    elif mode == 2:
        return 6005 * x ** 1.4


def levelget(exp, mode=0, all=None):
    x = 1
    lvlexp = levelmode(1, mode)
    while True:
        if exp > lvlexp:
            exp -= lvlexp
            x += 1
            lvlexp = levelmode(x, mode) - levelmode(x - 1, mode)
        elif all:
            return [x, int(exp), int(lvlexp)]
        else:
            return x


class TessMem:
    def __init__(self, data):
        self.id, self.server, self.nick, self.name, self.exp, self.allmessages, self.messages, self.symbols, self.pictures, self.online = data

    async def addexp(self, eadd, mem, reason=''):
        if eadd == 0:
            return

        try:
            roles = [i.id for i in mem.roles]
            if congrats in roles:
                eadd = int(eadd * ek_congrats)
        except:
            pass

        lvl = levelget(self.exp)
        self.exp += eadd
        if reason:
            if reason != 'online':
                print(f'{self.nick} получил {eadd} exp ({reason})')
        else:
            print(f'{self.nick} получил {eadd} exp')
        lvl_new = levelget(self.exp)
        # if lvl_new > lvl:
            # await channel.send(f'Повышение! у {rolemention(self)} **{lvl_new}** уровень!')


def TELoad():
    global expd
    SQL.execute('SELECT * FROM exp')
    mems = SQL.fetchall()
    for i in mems:
        expd[i[1]][i[0]] = TessMem(i)
    for g in bot.guilds:
        for m in g.members:
            try:
                if not expd[g.id][m.id]:
                    print(g.id, m.id)
            except:
                expd[g.id][m.id] = TessMem([g.id, m.id, m.name, '', 0, 0, 0, 0, 0, 0])


def TESavedef():
    for g in expd:
        if g == 822075570006654976:
            continue
        for m in expd[g]:
            i = expd[g][m]
            SQL.execute(f'SELECT * FROM exp WHERE id = {m} AND server = {g}')
            u = SQL.fetchall()
            if not u:
                sql_insert = 'INSERT INTO exp(id, server, nick, exp, allmessages, messages, symbols, pictures, online) VALUES (?,?,?,?,?,?,?,?,?)'
                SQL.execute(sql_insert, (m, g, i.nick, i.exp, i.allmessages, i.messages, i.symbols, i.pictures, i.online))
                db.commit()
            else:
                SQL.execute(f"UPDATE exp SET exp = {i.exp}, allmessages = {i.allmessages}, messages = {i.messages}, symbols = {i.symbols}, pictures = {i.pictures}, online = {i.online} WHERE id = {m} AND server = {g}")
                db.commit()


async def TESavetask():
    while not bot.is_closed():
        TESavedef()
        await asyncio.sleep(e_savetime)


async def online_counter():
    while not bot.is_closed():
        trans_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=e_onlinetime)
        for g in bot.guilds:
            mems = []
            for c in g.text_channels:
                async for mes in c.history(after=trans_time):
                    mems.append(mes.author.id)
            for v in g.voice_channels:
                if len(v.members) > 1:
                    for m in v.members:
                        if m.voice and not m.voice.deaf and not m.voice.self_deaf:
                            mems.append(m.id)
            mems = list(set(mems))
            for m in mems:
                mem = g.get_member(m)
                await expd[g.id][m].addexp(e_online, mem, 'online')
                expd[g.id][m].online += e_onlinetime
            if g.id == tessguildid:
                tt = time.time()
                lsn = -1
                for i, l in enumerate(lessons):
                    if tt > l and tt <= l + 4800:
                        lsn = i
                if lsn >= 0:
                    for m in mems:
                        if m in admins:
                            continue
                        SQL.execute(f'SELECT * FROM les_online WHERE les = {lsn} AND user = {m} ')
                        if not SQL.fetchone():
                            SQL.execute('INSERT INTO les_online(les,user) VALUES (?,?)', (lsn, m))
                    db.commit()
        await asyncio.sleep(e_onlinetime*60)


@bot.event
async def on_ready():
    global logchannel
    global hwchannel
    global dima
    TELoad()
    gr = 'Кубоид интегрировался в трёхмерное пространство'
    logchannel = bot.get_channel(botcage)
    hwchannel = bot.get_channel(hwchannelid)
    dima = bot.get_user(dimaid)
    bot.loop.create_task(TESavetask())
    bot.loop.create_task(online_counter())
    await logchannel.send(gr)
    print(gr)


@bot.event
async def on_message(message):
    await TessExp(message)
    await bot.process_commands(message)
    if message.channel.id == hwchannelid:
        if message.author.id in admins:
            return
        tt = time.time()
        lsn = 0
        for i,l in enumerate(lessons):
            if tt > l:
                lsn = i
        add_name = f' (**{message.author.name}**)' if message.author.name != message.author.display_name else ''
        async for i in dima.history():
            await i.delete()
        await dima.send(f'Домашка от пользователя {message.author.display_name}{add_name} за **{lsn}** занятие\nОтветить: {prefix}d {message.author.id} {lsn} <балл> <комментарий>')
        await dima.send(message.content)
        for a in message.attachments:
            await dima.send(attachment=a)
        await message.delete()


@bot.event
async def on_message_edit(message):
    await bot.process_commands(message)


@bot.event
async def on_member_join(m):
    g = m.guild
    try:
        if not expd[g.id][m.id]:
            print(g.id, m.id)
    except:
        expd[g.id][m.id] = TessMem([g.id, m.id, m.name, '', 0, 0, 0, 0, 0, 0])


async def TessExp(mes):
    atts = len(mes.attachments)
    eadd = 0
    g = mes.guild.id if mes.guild else tessguildid
    m = mes.author.id

    expd[g][m].allmessages += 1
    expd[g][m].pictures += atts

    if len(mes.content) > 0:
        expd[g][m].messages += 1
        expd[g][m].symbols += len(mes.content)
        if len(mes.content) > e_message * 3:
            eadd += len(mes.content)
        else:
            eadd += e_message
    eadd += atts * e_picture

    await expd[g][m].addexp(eadd, mes.author)


@bot.command()
async def exp(ctx):
    newvehicles = tesort([expd[ctx.guild.id][e] for e in expd[ctx.guild.id]])
    embed = discord.Embed(title=f'Опыт {ctx.guild.name}', colour=random.choice(raincolors))
    memids = [x.id for x in ctx.guild.members]
    memids.pop(memids.index(admins[0]))
    all_list = [0, 0, 0, 0, 0, 0]
    for i in newvehicles:
        all_list[0] += i.exp
        all_list[1] += i.allmessages
        all_list[2] += i.messages
        all_list[3] += i.symbols
        all_list[4] += i.pictures
        all_list[5] += i.online
    all = TessMem([ctx.guild.id, 1, 'All', 'All']+all_list)
    text = f'Все 🧊'
    text += f'   сообщений: {all.allmessages}'
    text += f', текстовых: {all.messages}'
    text += f', символов: {all.symbols}'
    text += f', картиночек: {all.pictures}'
    text += f', часов онлайн: {all.online // 60}'
    embed.add_field(name=f'Опыт: {all.exp}', value=text, inline=False)
    for i in newvehicles:
        if i.id in memids:
            lvl = levelget(i.exp, all=True)
            mem = ctx.guild.get_member(i.id)
            text = f'{mem.display_name} **{lvl[0]}** уровня'
            if i.allmessages:
                text += f', сообщений: {i.allmessages}'
            if i.messages:
                text += f', текстовых: {i.messages}'
            if i.symbols:
                text += f', картиночек: {i.symbols}'
            if i.pictures:
                text += f', картиночек: {i.pictures}'
            if i.online:
                online = f'{i.online // 60}ч {i.online % 60}мин'
                text += f', онлайн: {online}'
            prog = int(round((lvl[1] / lvl[2]) * 20))
            prog = f"{'▓' * prog}{'░' * (20 - prog)}"
            perc = f'{round((lvl[1] / lvl[2]) * 100, 2)}%'
            embed.add_field(name=f'Опыт: {i.exp}, {prog} {perc}', value=text, inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def d(ctx, id, lesson, grade, *comm):
    comm = ''.join(comm)
    mem = bot.get_user(int(id))
    text = f'Домашка к занятию **{lesson}** проверена! У вас **{grade}** {postfix(int(grade), ["балл", "балла", "баллов"], False)}.'
    if comm:
        text += f' Комментарий:\n{comm}'
    await mem.send(text)


token = open('tess_token.txt').readlines()[0]
bot.run(token)

