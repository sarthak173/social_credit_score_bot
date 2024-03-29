import os
import discord
import pandas as pd
import sqlite3

from dotenv import load_dotenv
from discord.ext import commands
from sqlite3 import OperationalError

from sql_utils import execute_query, connect_and_get_guild
from df_embed_utils import save_df_as_image
from constants import CCP_ROLES 

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
# async def on_member_join(member):
#     print("someone joined")
#     print(member)

@bot.command(name="bm")
async def wish_gm(ctx):
    # bm responds with gm
    response = "gm arctan"
    await ctx.send(response)

@bot.command(name="gm")
async def wish_gm(ctx):
    """
    Wishes the user gm
    Args:
        ctx: discord context object
    """
    if ctx.message.author == bot.user:
        return
    
    if "gm" in str(ctx.message.content).lower():
        if ctx.message.author.nick is not None:
            response = f"gm {ctx.message.author.nick}"
        else: 
            response = f"gm {ctx.message.author.global_name}"
        await ctx.send(response)
        
@commands.command(name="view")
async def view(ctx):
    """
    View command to see top 10 users by credit score for the current guild (server)
    Args:
        ctx: discord context object
    """
    conn = sqlite3.connect('social_credit.db')
    cursor = conn.cursor()
    curr_guild = ctx.guild
    sql_query = f"SELECT * FROM social_credit_scores WHERE guild_id = {curr_guild.id} ORDER BY credit_score DESC LIMIT 10"
    response = pd.read_sql_query(sql_query, conn)
    scores = response[["username", "credit_score"]]
    scores_dict = dict(zip(response['username'], response['credit_score']))

    embed = discord.Embed(title="Social Credit Scores", description="Current Top 10 Social Credit Scores")
    embed.add_field(name=curr_guild.name, value=(scores.to_markdown()), inline=True)
    await ctx.send(embed=embed)
    

@commands.command(name="init")
async def initialize(ctx):
    """
    Command to set up the social credit score table for a server. Should only be used once. Will return an error 
    message on multiple attempts to initialize.
    Args:
        ctx: discord context object
    """
    conn = sqlite3.connect('social_credit.db')
    cursor = conn.cursor()
    curr_guild = ctx.guild
    cursor.execute("SELECT * FROM social_credit_scores WHERE guild_id = ?", (curr_guild.id,))
    if cursor.fetchone() is not None:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Table already exists for {curr_guild.name}")
        await ctx.send(embed=embed)
        return

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
                    if "Drug Dealer" in CCP_ROLES:
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

@commands.command(pass_context=True, name="viewuser")
async def view_user(ctx, user: discord.User):
    """
    fetches the username and displays their credit score information
    Args:
        ctx: discord context object
        username: username to display the information for (needs to be discord username. Nickname/global name won't work)
    """
    if user is None:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Please specify a username")
        await ctx.send(embed=embed)
        return
    if isinstance(user, discord.User):
        username = user.name
    else:
        username = user
    conn = sqlite3.connect('social_credit.db')
    cursor = conn.cursor()
    curr_guild = ctx.guild
    sql_query = f"SELECT username, credit_score FROM social_credit_scores WHERE guild_id = {curr_guild.id} AND username = \"{username}\""
    response = pd.read_sql_query(sql_query, conn)
    if len(response) == 0:
        embed = discord.Embed(description=f"🔴 **FAILURE**: User does not exist in {curr_guild.name}")
        await ctx.send(embed=embed)
        return
    embed = discord.Embed(title="Social Credit Scores", description="Current Social Credit Scores")
    embed.add_field(name=curr_guild.name, value=(response.to_markdown()), inline=True)
    conn.close()
    await ctx.send(embed=embed)


@commands.command(name="viewbottom")
async def view_bot(ctx):
    conn, cursor, curr_guild = connect_and_get_guild(ctx)
    sql_query = f"SELECT username, credit_score FROM social_credit_scores WHERE guild_id = {curr_guild.id} ORDER BY credit_score ASC LIMIT 10"
    response = pd.read_sql_query(sql_query, conn)
    scores = response[["username", "credit_score"]]
    embed = discord.Embed(title="Social Credit Scores", description="Bottom 10 Social Credit Scores")
    embed.add_field(name=curr_guild.name, value=(scores.to_markdown()), inline=True)
    await ctx.send(embed=embed)
    conn.close()
    pass

@commands.command(name="update")
async def update_table(ctx):
    conn, cursor, curr_guild = connect_and_get_guild(ctx)
    guild_members = []
    member_id_dict = {}
    for member in curr_guild.members:
        if not member.bot:
            guild_members.append(str(member))
            member_id_dict[str(member)] = member.id
    sql_query = f"SELECT username FROM social_credit_scores WHERE guild_id = {curr_guild.id}"
    response = pd.read_sql_query(sql_query, conn)
    db_members_list = response['username']
    users_not_in_db = set(guild_members) - set(db_members_list)
    values = []
    members = [member async for member in curr_guild.fetch_members()]
    for user in users_not_in_db:
        missing_user = member_id_dict[user]
        print(missing_user)
        user_values = (missing_user, user, curr_guild.id, 500, False)
        values.append(user_values)
    for missing_user in values:
        insert_sql = """INSERT INTO social_credit_scores (user_id, username, guild_id, credit_score, is_admin)
                                VALUES (?, ?, ?, ?, ?)
                """
        try:
            cursor.execute(insert_sql, missing_user)
            conn.commit() 
        except Exception as msg:
            embed = discord.Embed(description=f"🔴 **FAILURE**: Could not add user to {curr_guild.name}")
            await ctx.send(embed=embed)
            return
    conn.close()
    embed = discord.Embed(description=f"🟢 **SUCCESS**: Table successfully updated for {curr_guild.name}")
    await ctx.send(embed=embed)
    
@commands.command(pass_context=True, name="updatescore")
async def update_score(ctx, user: discord.User, score: int):
    # check arguments are specified
    if user is None:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Please specify a username")
        await ctx.send(embed=embed)
        return
    if score is None:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Please specify a score")
        await ctx.send(embed=embed)
        return
    if not isinstance(score, int):
        embed = discord.Embed(description=f"🔴 **FAILURE**: Please specify an integer value")
        await ctx.send(embed=embed)
        return
    
    conn, cursor, curr_guild = connect_and_get_guild(ctx)
    if ctx.message.author == bot.user:
        return
    if isinstance(user, discord.User):
        username = user.name
    else:
        username = user
    print(username)
    admin_sql_query = f"SELECT is_admin FROM social_credit_scores WHERE guild_id = {curr_guild.id} AND username = \"{ctx.message.author.name}\""
    result = cursor.execute(admin_sql_query)
    rows = result.fetchone()
    print(rows)
    # check if user has update perms
    if rows[0] == 0:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Only CCP officials can update credit score")
        await ctx.send(embed=embed)
        return
    
    sql_query = f"SELECT username, credit_score FROM social_credit_scores WHERE guild_id = {curr_guild.id} AND username = \"{username}\""
    response = pd.read_sql_query(sql_query, conn)
    # check if user exists in guild and db
    if len(response) == 0:
        embed = discord.Embed(description=f"🔴 **FAILURE**: User does not exist in {curr_guild.name}")
        await ctx.send(embed=embed)
        return
    
    scores_dict = dict(zip(response['username'], response['credit_score']))
    print(scores_dict)
    curr_score = scores_dict[username]
    scores_dict[username] = curr_score + score
    print(scores_dict)
    update_query = f"UPDATE social_credit_scores SET credit_score = {scores_dict[username]} WHERE username = \"{username}\" AND guild_id = {curr_guild.id}"
    conn.execute(update_query)
    conn.commit()
    updated_data = pd.DataFrame(scores_dict, index=[0])
    embed = discord.Embed(description=f"🟢 **SUCCESS**: Credit score updated for {username}")
    await ctx.send(embed=embed)

    embed = discord.Embed(title="Social Credit Scores", description="Current Social Credit Scores")
    embed.add_field(name=curr_guild.name, value=(updated_data.to_markdown()), inline=True)
    conn.close()
    await ctx.send(embed=embed)

@commands.command(pass_context=True, name="makecommie")
async def make_admin(ctx, user: discord.User):
    if user is None:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Please specify a username")
        await ctx.send(embed=embed)
        return
    conn, cursor, curr_guild = connect_and_get_guild(ctx)
    if isinstance(user, discord.User):
        username = user.name
    else:
        username = user

    admin_sql_query = f"SELECT is_admin FROM social_credit_scores WHERE guild_id = {curr_guild.id} AND username = \"{ctx.message.author.name}\""
    result = cursor.execute(admin_sql_query)
    rows = result.fetchone()
   
    # check if user has update perms
    if rows[0] == 0:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Only CCP officials can grant admin access")
        await ctx.send(embed=embed)
        return
    
    update_query = f"UPDATE social_credit_scores SET is_admin = 1 WHERE username = \"{username}\" and guild_id = {curr_guild.id}"
    conn.execute(update_query)
    conn.commit()
    embed = discord.Embed(description=f"🟢 **SUCCESS**: {username} is now a member of the CCP")
    conn.close()
    await ctx.send(embed=embed)

@commands.command(pass_context=True, name="firecommie")
async def remove_admin(ctx, user: discord.User):
    if user is None:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Please specify a username")
        await ctx.send(embed=embed)
        return
    conn, cursor, curr_guild = connect_and_get_guild(ctx)
    
    admin_sql_query = f"SELECT is_admin FROM social_credit_scores WHERE guild_id = {curr_guild.id} AND username = \"{ctx.message.author.name}\""
    result = cursor.execute(admin_sql_query)
    rows = result.fetchone()
   
    # check if user has update perms
    if rows[0] == 0:
        embed = discord.Embed(description=f"🔴 **FAILURE**: Only CCP officials can fire commies")
        await ctx.send(embed=embed)
        return
    if isinstance(user, discord.User):
        username = user.name
    else:
        username = user
    update_query = f"UPDATE social_credit_scores SET is_admin = 1 WHERE username = \"{username}\" and guild_id = {curr_guild.id}"
    conn.execute(update_query)
    conn.commit()
    embed = discord.Embed(description=f"🟢 **SUCCESS**: {username}'s CCP pass has been revoked")
    conn.close()
    await ctx.send(embed=embed)

# add commands to the bot
bot.add_command(view)
bot.add_command(initialize)
bot.add_command(view_user)
bot.add_command(update_table)
bot.add_command(update_score)
bot.add_command(view_bot)
bot.add_command(make_admin)
bot.add_command(remove_admin)

bot.run(TOKEN)