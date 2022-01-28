import asyncio
import logging
import time

from aioconsole import ainput
from aiohttp import ClientSession, ClientWebSocketResponse
from aiohttp.http_websocket import WSMessage
from aiohttp.web import WSMsgType

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


async def connect_to_chat(ws):
    await asyncio.sleep(1)
    group_id = await ainput('Group Id: ')
    username = await ainput('Username:')
    await ws.send_json({'action': 'connect', 'username': username, 'group': group_id})


async def listen(ws):
    async for msg in ws:
        if msg.type == WSMsgType.text:
            message_json = msg.json()
            action = message_json.get('action')
            log.info('Notification: %s', message_json)
            if action == 'ws connection established':
                await connect_to_chat(ws)
            if action == 'group connection':
                is_success = message_json.get('is_success')
                if is_success:
                    last_messages = message_json.get('chat_history')
                    if last_messages:
                        for message in last_messages:
                            log.info('Notification: %s', message)
                    asyncio.create_task(send_msg(ws))
                else:
                    await connect_to_chat(ws)


async def send_msg(ws):
    while True:
        text = await ainput()
        if text == 'disconnect':
            await ws.send_json({'action': 'disconnect'})
            break
        if text.startswith('kick'):
            user = text.split()[-1]
            await ws.send_json({'action': 'kick', 'target_user': user})
        else:
            await ws.send_json({'action': 'message', 'text': text})


async def handle():
    async with ClientSession() as session:
        async with session.ws_connect('ws://localhost:8080/chat', ssl=False) as ws:
            await listen(ws)
        print('The chat was closed')
        if not ws.closed:
            await ws.close()


if __name__ == '__main__':
    asyncio.run(handle())
