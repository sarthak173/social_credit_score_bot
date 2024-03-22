import sqlite3

def execute_query(query, conn):
    if conn is not None:
        try:            
            output = ""
            c = conn.cursor()
            try:
                c.execute(query)
            except Exception as e:
                return e
            info = c.fetchall()
            conn.commit()
            for value in info:
                output += str(value) + "\n"
            if output=="":
                return "No Output / Empty"
            return output
        except Exception as e:
            return e
    return "Error! the database connection was not created."

def connect_and_get_guild(ctx):
    conn = sqlite3.connect('social_credit.db')
    cursor = conn.cursor()
    curr_guild = ctx.guild
    return conn, cursor, curr_guild