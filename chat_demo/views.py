import logging
import aiohttp
from aiohttp import web, WSCloseCode
import settings

log = logging.getLogger(__name__)


async def notify_all(app, group_id, message):
    for ws in app['chat'][group_id]['users'].values():
        await ws.send_json(message)


async def kick_user(app, current_ws, group_id, current_username, target_username):
    response_body = {'action': 'kick', 'is_success': False,
                     'message': ''}
    admin_name = app['chat'][group_id]['admin']
    if current_username!=target_username:
        if admin_name == current_username:
            if target_username in app['chat'][group_id]['users'].keys():
                response_body['is_success'] = True
                response_body['message'] = 'OK'
                target_user_ws = app['chat'][group_id]['users'][target_username]
                await target_user_ws.close()
            else:
                response_body['message'] = 'The user doesn`t exist'
        else:
            response_body['message'] = 'You don`t have rights to kick!'
    else:
        response_body['message'] = 'You can`t kick yourself!'
    return response_body


async def join_group(app, current_ws, group_id, username):
    response_body = {'action': 'group connection', 'is_success': False,
                     'message': ''}
    if 3 <= len(group_id) <= 8:
        if app['chat'].get(group_id):
            if app['chat'][group_id]['users_count'] < settings.MAX_USERS_IN_GROUP:
                if username in app['chat'][group_id]['users'].keys():
                    response_body['message'] = 'This nickname was already taken'
                else:

                    last_messages = app['chat'][group_id]['events'][-settings.MAX_MESSAGE_TO_STORE:]
                    response_body['is_success'] = True
                    response_body['message'] = 'OK'
                    response_body['chat_history'] = last_messages
                    app['chat'][group_id]['users'][username] = current_ws
                    app['chat'][group_id]['users_count'] += 1
            else:
                response_body['message'] = f'Group reached the limit of {settings.MAX_USERS_IN_GROUP} users'
        else:
            app['chat'][group_id] = {'users': {}, 'users_count': 1, 'events': [], 'admin': username}
            app['chat'][group_id]['users'][username] = current_ws
            response_body['is_success'] = True
            response_body['message'] = f'Group {group_id} was created.'
    else:
        response_body['message'] = 'The group id should be between 3-8 charact.'

    return response_body


async def chat(request):
    current_ws = web.WebSocketResponse()
    ready = current_ws.can_prepare(request=request)
    if not ready:
        await current_ws.close(code=WSCloseCode.PROTOCOL_ERROR)
    await current_ws.prepare(request)
    await current_ws.send_json({'action': 'ws connection established'})
    try:
        async for msg in current_ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                msg_json = msg.json()
                action = msg_json.get('action')
                if action == 'connect':
                    group_id, current_username = msg_json.get('group'), msg_json.get('username')
                    response = await join_group(request.app, current_ws, group_id, current_username)
                    await current_ws.send_json(response)
                    if response['is_success']:
                        message = {'action': 'new join', 'group': group_id, 'name': current_username}
                        await notify_all(request.app, group_id, message)
                elif action == 'message':
                    text = msg_json.get('text')
                    message = {'action': 'message', 'username': current_username, 'text': text}
                    request.app['chat'][group_id]['events'].append(message)
                    await notify_all(request.app, group_id, message)
                elif action == 'kick':
                    target_username = msg_json.get('target_user')
                    response = await kick_user(request.app, current_ws, group_id, current_username, target_username)
                    await current_ws.send_json(response)
                elif action == 'disconnect':
                    await current_ws.send_json(
                        {'action': 'disconnect', 'is_success': True, 'message': 'You were disconnected'})
                    break;
                else:
                    await current_ws.send_json(
                        {'action': action, 'is_success': False, 'message': 'Unknown command'})
    finally:
        if request.app['chat'][group_id]['users_count'] > 1:
            del request.app['chat'][group_id]['users'][current_username]
            request.app['chat'][group_id]['users_count'] -= 1
            message = {'action': 'disconnect', 'room': group_id, 'username': current_username}
            await notify_all(request.app, group_id, message)
        else:
            del request.app['chat'][group_id]
            log.info(f'Group {group_id} was deleted!')
    return current_ws
