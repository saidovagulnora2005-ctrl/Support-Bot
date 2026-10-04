from dotenv import load_dotenv
import asyncpg
import os

load_dotenv()


async def get_connection():
    try:
        conn = await asyncpg.connect(
            database = "support_bot",
            port = 5432,
            user = "postgres",
            password = os.getenv("SQL_PASSWORD"),
            host = "localhost"
        )
        return conn
    except Exception as error:
        print("Get connection error: ",error)


async def init_tables():
    conn = await get_connection()
    try:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets(
            id SERIAL PRIMARY KEY,
            telegram_id bigint,
            subject varchar(200) not null,
            description text not null,
            photo_file_id text,
            status varchar(20) check(status IN('open','closed')),
            created_at timestamp default now(),
            closed_at timestamp
        );
        CREATE TABLE IF NOT EXISTS ticket_messages(
            id SERIAL PRIMARY KEY,
            ticket_id INT REFERENCES tickets(id) ON DELETE CASCADE,
            sender_id bigint not null,
            sender_role varchar(20) check(sender_role IN('user','admin')),
            text TEXT not null,
            created_at timestamp default now()
        );
    """)
        print("Tables created successfully!")
    except Exception as error:
        print("Error in creating tables: ",error)
    finally:
        await conn.close()
