import os
from dotenv import load_dotenv
from groq import AsyncGroq
from connection import get_connection
from tavily import TavilyClient

load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AI_MODEL = os.getenv("AI_MODEL","openai/gpt-oss-20b")
client = AsyncGroq(api_key = GROQ_API_KEY)

ai_history = {}


def is_admin(telegram_id):
    return telegram_id == ADMIN_ID


async def create_ticket(telegram_id,subject,description,photo_file_id):
    conn = await get_connection()
    try:
        ticket_id = await conn.fetchval("""
            INSERT INTO tickets(telegram_id,subject,description,photo_file_id)
            VALUES($1, $2, $3, $4) RETURNING id
            """,telegram_id,subject,description,photo_file_id)
        return ticket_id
    except Exception as error:
        print("Created ticket error: ",error)
    finally:
        await conn.close()


async def get_user_tickets(telegram_id):
    conn = await get_connection()
    try:
        tickets = await conn.fetch("""
            SELECT id, subject, status, created_at FROM tickets WHERE telegram_id = $1 ORDER BY created_at DESC, id DESC
            """,telegram_id)
        return tickets
    except Exception as error:
        print("Get user tickets error: ",error)
    finally:
        await conn.close()


async def get_open_tickets():
    conn = await get_connection()
    try:
        tickets = await conn.fetch("""
            SELECT id, telegram_id, subject, status, created_at FROM tickets
            WHERE status = 'open' ORDER BY created_at ASC, id ASC
            """)
        return tickets
    except Exception as error:
        print("Get open tickets error: ",error)
    finally:
        await conn.close()


async def get_ticket(ticket_id,telegram_id):
    conn = await get_connection()
    try:
        ticket = await conn.fetchrow("""
            SELECT id,telegram_id,subject,description,photo_file_id,status,
            created_at,closed_at FROM tickets WHERE id = $1
            """,ticket_id)
        if ticket is None:
            return None
        if ticket["telegram_id"] != telegram_id and not is_admin(telegram_id):
            return None
        return ticket
    except Exception as error:
        print("Get ticket error: ",error)
    finally:
        await conn.close()


async def get_ticket_messages(ticket_id):
    conn = await get_connection()
    try:
        messages = await conn.fetch("""
            SELECT id,sender_id,sender_role,text,created_at
            FROM ticket_messages WHERE ticket_id = $1 ORDER BY created_at ASC, id ASC
            """,ticket_id)
        return messages
    except Exception as error:
        print("Get ticket messages error: ",error)
    finally:
        await conn.close()


async def add_user_message(ticket_id,telegram_id,text):
    conn = await get_connection()
    try:
        ticket = await conn.fetchrow("""
            SELECT id FROM tickets WHERE id = $1 AND telegram_id = $2 AND status = 'open'
            """,ticket_id,telegram_id)
        if ticket is None:
            return False
        await conn.execute("""
            INSERT INTO ticket_messages(ticket_id,sender_id,sender_role,text)
            VALUES($1, $2, 'user', $3)
            """,ticket_id,telegram_id,text)
        return True
    except Exception as error:
        print("Add user message error: ",error)
    finally:
        await conn.close()


async def add_admin_message(ticket_id,admin_id,text):
    if not is_admin(admin_id):
        return None
    conn = await get_connection()
    try:
        ticket = await conn.fetchrow("""
            SELECT id, telegram_id FROM tickets WHERE id = $1 AND status = 'open'
            """,ticket_id)
        if ticket is None:
            return None
        await conn.execute("""
            INSERT INTO ticket_messages(ticket_id,sender_id,sender_role,text)
            VALUES($1, $2, 'admin', $3)
            """,ticket_id,admin_id,text)
        return ticket
    except Exception as error:
        print("Add admin message error: ",error)
    finally:
        await conn.close()


async def close_ticket(ticket_id,admin_id):
    if not is_admin(admin_id):
        return "no_access"
    conn = await get_connection()
    try:
        ticket = await conn.fetchrow("""
            SELECT id, telegram_id, status FROM tickets WHERE id = $1
            """,ticket_id)
        if ticket is None:
            return "not_found"
        if ticket["status"] == "closed":
            return "closed"
        await conn.execute("""
            UPDATE tickets SET status = 'closed', closed_at = now()
            WHERE id = $1 AND status = 'open'
            """,ticket_id)
        return ticket
    except Exception as error:
        print("Close ticket error: ",error)
    finally:
        await conn.close()


def clear_ai_history(telegram_id):
    ai_history.pop(telegram_id,None)



tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
AI_MODEL = os.getenv("AI_MODEL")
ai_history = {}


def search_alif(text):
    response = tavily.search(
        query = f"site:alif.tj Alif Bank Таджикистан {text}",
        search_depth = "basic",
        max_results = 5,
        include_domains = ["alif.tj"]
    )
    results = response["results"]
    if not results:
        return "Информация не найдена."
    information = ""
    for result in results:
        information += (
            f"Источник: {result['url']}\n"
            f"Информация: {result['content']}\n\n")
    return information


async def ask_ai(telegram_id, text):
    if telegram_id not in ai_history:
        ai_history[telegram_id] = [
            {
                "role": "system",
                "content": """
Ты — AI-консультант Alif Bank в Душанбе.
Помогай пользователям только по вопросам, связанным с Alif Bank и его услугами.
Используй информацию из найденных материалов официального сайта Alif Bank.

Не выдумывай информацию.
Если в найденной информации нет ответа, скажи:
"Я не нашёл точной информации по этому вопросу. Пожалуйста, обратитесь в службу поддержки Alif Bank."

Отвечай понятно, вежливо и кратко.

Если пользователь пишет на русском — отвечай на русском.
Если пользователь пишет на таджикском — отвечай на таджикском.
Если пользователь пишет на английском — отвечай на английском.


Никогда не проси:
- пароль
- PIN-код
- CVV
- SMS-код
- полный номер банковской карты

Ты являешься AI-консультантом, а не настоящим сотрудником банка.
"""
            }
        ]
    search_results = search_alif(text)
    prompt = f"""
Вопрос пользователя:
{text}

Актуальная информация с официального сайта Alif Bank:
{search_results}

Ответь на вопрос пользователя, используя эту информацию.

Не придумывай данные, которых нет в найденной информации.
"""
    ai_history[telegram_id].append(
        {
            "role": "user",
            "content": prompt
        }
    )
    if len(ai_history[telegram_id]) > 21:
        ai_history[telegram_id] = [
            ai_history[telegram_id][0]
        ] + ai_history[telegram_id][-20:]
    response = await client.chat.completions.create(model = AI_MODEL,messages = ai_history[telegram_id])
    answer = response.choices[0].message.content
    ai_history[telegram_id].append(
        {
            "role": "assistant",
            "content": answer
        })
    return answer