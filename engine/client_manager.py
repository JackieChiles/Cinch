#!/usr/bin/python3
"""Client management class for web server.

"""
#from uuid import uuid4  # don't really need 32-byte ID
import random

# Constants for client id elements
CLIENT_NAME = 0
CLIENT_GROUP = 1
CLIENT_PLAYER_NUM = 2

MAX_GUID = 32767

class ClientManager:
    """Provide mapping functions for Clients with respect to the game engine.

    self.clients is a dictionary of lists, keyed by client guid.
    
    Clients have the following associations (keys):
    - name (str): user name for client
    - group (int): group/game number
    - playerNum (int): ID of Client within group
    
    """
    def __init__(self):
        """"""
        self.clients = dict()
        self.groups = dict()
        
    def add_client(self, name=None):
        """Create new client in internal map. Return client guid.

        name (str): player/user name for client [optional]
        
        """
        count = 0
        while True:
            guid = random.randint(0, MAX_GUID)

            # Verify guid unique in ClientManager
            if guid not in self.clients:
                break

            # Prevent infinite loops
            count += count
            if count == MAX_GUID:
                raise RuntimeError(
                    "Too many clients. Cannot create new client.")
               
        self.clients[guid] = [name, None, None] # Initialize client

        return guid

    def add_client_to_group(self, client, group):
        """Add client to group.

        In current implementation, clients can belong to at most 1 group.

        client (int): guid for client
        group (int): id for group
        
        """
        assert (client in self.clients.keys())
        assert (group in self.groups.keys())

        # Add group to client's info and reset playerNum
        self.clients[client][CLIENT_GROUP] = group
        self.clients[client][CLIENT_PLAYER_NUM] = None   # clear playerNum

        # Add client to group's info
        self.groups[group].append(client)

    def add_group(self, ident):
        """Create group.

        ident (int): id for group

        """
        if ident in self.groups.keys():
            raise Exception("Group {0} already exists.".format(ident))
        
        self.groups[ident] = None

    def del_client(self, ident):
        """Delete client and remove from its group (if applicable).

        ident (int): guid for client

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

    def get_clients_in_group(self, group):
        """Return list of clients associated with group.

        group (int): id for group

        """
        try:
            return self.groups[group]
        except KeyError:
            raise KeyError("Group {0} does not exist.".format(group))

    def get_group_by_client(self, client):
        """Return group that contains client.

        client (int): guid of client

        """
        try:
            return self.clients[client][CLIENT_GROUP]
        except KeyError:
            raise KeyError("Client {0} does not exist.".format(client))

    def get_player_num_by_client(self, client):
        """Return playerNum for client.

        client (int): guid of client

        """
        try:
            return self.clients[client][CLIENT_PLAYER_NUM]
        except KeyError:
            raise KeyError("Client {0} does not exist.".format(client))            

    def set_client_name(self, client, name):
        """Set name for client.

        client (int): guid for client
        name (str): player name for client

        """
        assert (client in self.clients.keys())
        assert isinstance(name, str)
        
        self.clients[client][CLIENT_NAME] = name

    def set_client_player_num(self, client, playerNum):
        """Set player number for client.

        client (int): guid for client
        playerNum (int): id for player within player's group

        """
        assert (client in self.clients.keys())
        assert isinstance(playerNum, int)
        
        self.clients[client][CLIENT_PLAYER_NUM] = playerNum
