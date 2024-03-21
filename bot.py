import os
import discord
import pandas as pd
import sqlite3

from dotenv import load_dotenv
from discord.ext import commands
from sqlite3 import OperationalError

from sql_utils import execute_query
from df_embed_utils import save_df_as_image


conn = sqlite3.connect('social_credit.db')
cursor = conn.cursor()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents(members=True, messages=True, guilds=True)
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(intents=intents, command_prefix="!")

@bot.event
async def on_ready():
    guild = discord.utils.find(lambda g: g.name == GUILD, bot.guilds)
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )
    members = [member async for member in guild.fetch_members()]
    for member in members:
        print(member.name)
    fd = open("create_social_credit.sql", "r")
    create_table = fd.read()
    fd.close()

    try:
        cursor.execute(create_table)
    except OperationalError as msg:
        print("Create Table Failed: ", msg)
    

# @bot.event
# async def on_message(message):
    
#     if message.author == bot.user:
#         return
    
#     if "gm" in str(message.content).lower():
#         if message.author.nick is not None and message.author != bot.user:
#             response = f"gm {message.author.nick}" 
#         response = f"gm {message.author.global_name}"
#         await message.channel.send(response)

@bot.command(name="bm")
async def wish_gm(ctx):
    #bm responds with gm
    response = "gm arctan"
    await ctx.send(response)
        
@commands.command(name="view")
async def view(ctx):
    conn = sqlite3.connect('social_credit.db')
    cursor = conn.cursor()
    curr_guild = ctx.guild
    sql_query = f"SELECT * FROM social_credit_scores WHERE guild_id = {curr_guild.id}"
    response = pd.read_sql_query(sql_query, conn)
    scores = response[["username", "credit_score"]]
    scores_dict = dict(zip(response['username'], response['credit_score']))

    embed = discord.Embed(title="Social Credit Scores", description="Current Social Credit Scores")
    embed.add_field(name=curr_guild.name, value=(scores.to_markdown()), inline=True)
    await ctx.send(embed=embed)
    

@commands.command(name="init")
async def initialize(ctx):
    conn = sqlite3.connect('social_credit.db')
    cursor = conn.cursor()
    curr_guild = ctx.guild
    cursor.execute("SELECT * FROM social_credit_scores WHERE guild_id = ?", (curr_guild.id,))
    if cursor.fetchone() is not None:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Table already exists for {curr_guild.name}")
        await ctx.send(embed=embed)

    cursor.execute("SELECT * FROM social_credit_scores WHERE guild_id = ?", (curr_guild.id,))
    if cursor.fetchone() is None:
        for member in curr_guild.members:
            # is_admin = False
            # for role in member.roles:
            #     if "Drug Dealer" in role.name:
            #         is_admin = True
            # values = (member.id, str(member), curr_guild.id, 500, is_admin)
            # print(values)
            if not member.bot:
            
                insert_sql = """INSERT INTO social_credit_scores (user_id, username, guild_id, credit_score, is_admin)
                                VALUES (?, ?, ?, ?, ?)
                """
                is_admin = False
                credit_score = 500
                for role in member.roles:
                    if "Drug Dealer" in role.name:
                        is_admin = True
                        credit_score = 1000
                values = (member.id, str(member), curr_guild.id, credit_score, is_admin)
                cursor.execute(insert_sql, values)
                print(f"[User-Check] Added {member.name} to SQLite Database.")
                conn.commit()
            else:
                continue
        
    embed = discord.Embed(description=f"🟢 **SUCCESS**: Social Credit Score Table set up succesfully for {curr_guild.name}")
   
    conn.close()
    await ctx.send(embed=embed)

bot.add_command(view)
bot.add_command(initialize)

bot.run(TOKEN)