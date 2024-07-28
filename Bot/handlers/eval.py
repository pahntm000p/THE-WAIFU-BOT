import io
import os
import textwrap
import traceback
from contextlib import redirect_stdout
from pyrogram import Client, filters
from pyrogram.types import Message
from ..config import OWNER_ID
from pyrogram.enums import ParseMode

namespaces = {}

def namespace_of(chat, message, client):
    if chat not in namespaces:
        namespaces[chat] = {
            "__builtins__": globals()["__builtins__"],
            "client": client,
            "message": message,
            "from_user": message.from_user,
            "chat": message.chat,
        }
    return namespaces[chat]

def log_input(message):
    user = message.from_user.id
    chat = message.chat.id
    print(f"IN: {message.text} (user={user}, chat={chat})")

async def send(msg, client, message):
    if len(str(msg)) > 2000:
        with io.BytesIO(str.encode(msg)) as out_file:
            out_file.name = "output.txt"
            await client.send_document(
                chat_id=message.chat.id, 
                document=out_file,
                reply_to_message_id=message.id
            )
    else:
        print(f"OUT: '{msg}'")
        await client.send_message(
            chat_id=message.chat.id,
            text=f"`{msg}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=message.id
        )

async def evaluate(client: Client, message: Message):
    await send(await do(eval, client, message), client, message)

def cleanup_code(code):
    if code.startswith("```") and code.endswith("```"):
        return "\n".join(code.split("\n")[1:-1])
    return code.strip("` \n")

async def do(func, client, message):
    log_input(message)
    content = message.text.split(" ", 1)[-1]
    body = cleanup_code(content)
    env = namespace_of(message.chat.id, message, client)

    os.chdir(os.getcwd())
    with open("temp.txt", "w") as temp:
        temp.write(body)

    stdout = io.StringIO()

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    try:
        exec(to_compile, env)
    except Exception as e:
        return f"{e.__class__.__name__}: {e}"

    func = env["func"]

    try:
        with redirect_stdout(stdout):
            func_return = await func()
    except Exception as e:
        value = stdout.getvalue()
        return f"{value}{traceback.format_exc()}"
    else:
        value = stdout.getvalue()
        result = None
        if func_return is None:
            if value:
                result = f"{value}"
            else:
                try:
                    result = f"{repr(eval(body, env))}"
                except:
                    pass
        else:
            result = f"{value}{func_return}"
        if result:
            return result

async def clear(client: Client, message: Message):
    log_input(message)
    global namespaces
    if message.chat.id in namespaces:
        del namespaces[message.chat.id]
    await send("Cleared locals.", client, message)

def add_eval_handlers(app: Client):
    app.on_message(filters.command(["eval", "exec", "py"]) & filters.user(OWNER_ID))(evaluate)
    app.on_message(filters.command("clearlocals") & filters.user(OWNER_ID))(clear)
