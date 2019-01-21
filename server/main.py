import asyncio
import websockets
import json
import uuid
from game import Game

user_websockets = {}
games = []


def log(message):
    print(message)


async def start_new_game(websocket, data):
    log('New game started')
    games.append(Game())


async def join_game(websocket, data):
    try:
        game_id = data['gameId']
    except KeyError:
        log('Game ID not specified in join request.')
    else:
        log(f'Joining game {game_id}')


async def leave_game(websocket, data):
    log('Leaving current game')


async def bid(websocket, data):
    try:
        value = data['value']
    except KeyError:
        log('Value not specified in bid request.')
    else:
        log(f'Bidding {value}')


async def play(websocket, data):
    try:
        value = data['value']
    except KeyError:
        log('Value not specified in play request.')
    else:
        log(f'Playing card {value}')


async def chat(websocket, data):
    try:
        value = data['value']
    except KeyError:
        log('Value not specified in chat request.')
    else:
        log(f'Chat sent: {value}')


async def get_games_list(websocket, data):
    log('Games list retrieved')
    await send_data(websocket, {'games': games})


actions = {
    'new': start_new_game,
    'list-games': get_games_list,
    'join': join_game,
    'leave': leave_game,
    'bid': bid,
    'play': play,
    'chat': chat
}


async def receive_message(websocket, message):
    # TODO handle json load errors
    data = json.loads(message)

    try:
        action = data['action']
    except KeyError:
        log('Action not specified. Message ignored.')
    else:
        try:
            handler = actions[action]
        except KeyError:
            log(f'Handler for action {action} not found.')
        else:
            await handler(websocket, data)


async def send_message(websocket, message):
    await websocket.send(message)


async def send_data(websocket, data):
    # TODO handle json encode errors
    await send_message(websocket, json.dumps(data))


async def send_user_data(data, user_id):
    try:
        websocket = user_websockets[user_id]
    except KeyError:
        log(f'Socket for user {user_id} not found. Could not send message.')
    else:
        await send_data(websocket, data)


async def socket_handler(websocket, path):
    user_id = uuid.uuid4()
    user_websockets[user_id] = websocket

    async for message in websocket:
        await receive_message(websocket, message)

start_server = websockets.serve(socket_handler, '0.0.0.0', 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
