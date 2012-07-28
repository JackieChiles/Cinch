#!/usr/bin/python3
"""Client management class for web server.

Client manager supports the following methods:

add_client_to_group(self, client, group)
create_client(self, name=None)
create_group(self)
del_client(self, ident)
del_group(self, ident)
get_client_by_player_num(self, group, pNum)
def get_client_info(self, client)
get_clients_in_group(self, group)
get_group_by_client(self, client)
get_player_num_by_client(self, client)
get_player_nums_in_group(self, group)
set_client_name(self, client, name)
set_client_player_num(self, client, playerNum)

FUTURE: remove unused methods
TODO: review this module for accuracy of documentation/descriptions

"""
import string
import random

# Constants for client id elements
CLIENT_NAME = 0
CLIENT_GROUP = 1
CLIENT_PLAYER_NUM = 2

MAX_TRIES = 32767


def generate_id(size=6):
    """Generate random character string of specified size.

    Uses digits, upper- and lower-case letters.
    
    """
    chars=string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for x in range(size))


class ClientManager:
    """Provide mapping functions for Clients with respect to the game engine.

    self.clients is a dictionary of lists, keyed by client guid (str).
    
    Clients have a list with the following values:
    - name (str): user name for client
    - group (int): group/game number
    - playerNum (int): ID of Client within group

    self.groups is a dictionary, keyed by game id (int). The value of each
    group is a list of client guids that are in the group.
    
    """
    def __init__(self):
        """"""
        self.clients = dict()
        self.groups = dict()
        
    def add_client_to_group(self, client, group, pNum):
        """Add client to group.

        In current implementation, clients can belong to at most 1 group.

        client (str): guid for client
        group (int): id for group
        pNum (int): player number within group
        
        """
        assert (client in self.clients.keys())
        assert (group in self.groups.keys())

        # Add group and pNum to client's info
        self.clients[client][CLIENT_GROUP] = group
        self.clients[client][CLIENT_PLAYER_NUM] = pNum

        # Add client to group's info
        cur_group = self.groups[group]
        try:
            cur_group[pNum] = client
        except IndexError: # Group is not long enough, so extend
            cur_group.extend([None]*(pNum - len(cur_group) + 1))
            cur_group[pNum] = client
        

    def create_client(self, name=None):
        """Create new client in internal map. Return client guid.

        name (str): player/user name for client [optional]
        
        """
        count = 0
        while True:
            guid = generate_id()

            # Verify guid unique in ClientManager
            if guid not in self.clients.keys():
                break

            # Prevent infinite loops
            count += count
            if count > MAX_TRIES:
                return None # Server unable to create new player
               
        self.clients[guid] = [name, None, None] # Initialize client

        return guid

    def create_group(self):
        """Create new group and return group ID.

        Groups are sequentially numbered.

        """
        try:
            last_group = max(self.groups.keys())
        except ValueError:
            last_group = -1

        ident = last_group + 1        
        self.groups[ident] = []     # client IDs will be added to this list

        return ident

    def del_client(self, ident):
        """Delete client and remove from its group (if applicable).

        ident (str): guid for client

        """
        try:
            group = self.clients[ident][CLIENT_GROUP]
            del self.clients[ident]

        except KeyError:
            raise KeyError("Client {0} does not exist.".format(ident))

        if groups is not None:
            try:
                self.groups[group].remove(ident)
            except KeyError:
                raise KeyError("Group {0} does not exist.".format(group))

    def del_group(self, ident):
        """Delete group and clear group assignments of associated clients.

        ident (int): id for group

        """
        try:
            for client in self.groups[ident]:
                client[CLIENT_GROUP] = None

            del self.groups[ident]
        except KeyError:
            raise KeyError("Group {0} does not exist.".format(ident))

    def get_client_by_player_num(self, group, pNum):
        """Return client guid of player pNum from group.

        group (int): id for group
        pNum (int): local player num w/in group

        """
        for client_id in self.groups[group]:
            if self.clients[client_id][CLIENT_PLAYER_NUM] == pNum:
                return client_id

        return None

    def get_client_info(self, client):
        """Return group_id, playerNum for client.

        client (str): guid of client

        """
        try:
            group = self.clients[client][CLIENT_GROUP]
            pNum = self.clients[client][CLIENT_PLAYER_NUM]
            return group, pNum
        except KeyError:
            raise KeyError("Client {0} does not exist.".format(client))

    def get_clients_in_group(self, group):
        """Return list of clients associated with group.

        group (int): id for group

        """
        try:
            return [x for x in self.groups[group] if x is not None]
        except KeyError:
            raise KeyError("Group {0} does not exist.".format(group))
        
    def get_group_by_client(self, client):
        """Return group that contains client.

        client (str): guid of client

        """
        try:
            return self.clients[client][CLIENT_GROUP]
        except KeyError:
            raise KeyError("Client {0} does not exist.".format(client))

    def get_player_num_by_client(self, client):
        """Return playerNum for client.

        client (str): guid of client

        """
        try:
            return self.clients[client][CLIENT_PLAYER_NUM]
        except KeyError:
            raise KeyError("Client {0} does not exist.".format(client))
    
    def get_player_names_in_group(self, group):
        """Return dict of player num & name for clients in group.
        
        group (int): group id
        
        """
        players = {} # Key = pNum, value = name
        try:
            client_guids = [x for x in self.groups[group] if x is not None]
            for c in client_guids:
                pNum = self.clients[c][CLIENT_PLAYER_NUM]
                name = self.clients[c][CLIENT_NAME]
                players[pNum] = name
            
            return players
        
        except KeyError:
            return "Cannot get player numbers from Group {0}".format(group)

    def get_player_nums_in_group(self, group):
        """Return list of player numbers of clients in group.

        group (int): group id

        """
        pNums = []
        try:
            client_guids = [x for x in self.groups[group] if x is not None]
            for c in client_guids:
                pNums.append(self.clients[c][CLIENT_PLAYER_NUM])

            return pNums

        except KeyError:
            return "Cannot get player numbers from Group {0}".format(group)

    def set_client_name(self, client, name):
        """Set name for client.

        client (str): guid for client
        name (str): player name for client

        """
        assert (client in self.clients.keys())
        assert isinstance(name, str)
        
        self.clients[client][CLIENT_NAME] = name

    def set_client_player_num(self, client, playerNum):
        """Set player number for client.

        client (str): guid for client
        playerNum (int): id for player within player's group

        """
        assert (client in self.clients.keys())
        assert isinstance(playerNum, int)
        
        self.clients[client][CLIENT_PLAYER_NUM] = playerNum

