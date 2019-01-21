import asyncio
import websockets
import json
from game import Game

games = []


def log(message):
    print(message)


def start_new_game(data):
    log('New game started')
    games.append(Game())


def join_game(data):
    try:
        game_id = data['gameId']
    except KeyError:
        log('Game ID not specified in join request.')
    else:
        log(f'Joining game {game_id}')


def leave_game(data):
    log('Leaving current game')


def bid(data):
    try:
        value = data['value']
    except KeyError:
        log('Value not specified in bid request.')
    else:
        log(f'Bidding {value}')


def play(data):
    try:
        value = data['value']
    except KeyError:
        log('Value not specified in play request.')
    else:
        log(f'Playing card {value}')


def chat(data):
    try:
        value = data['value']
    except KeyError:
        log('Value not specified in chat request.')
    else:
        log(f'Chat sent: {value}')


actions = {
    'new': start_new_game,
    'join': join_game,
    'leave': leave_game,
    'bid': bid,
    'play': play,
    'chat': chat
}


def process_message(message):
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
            handler(data)


async def socket_handler(websocket, path):
    async for message in websocket:
        process_message(message)

start_server = websockets.serve(socket_handler, '0.0.0.0', 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
