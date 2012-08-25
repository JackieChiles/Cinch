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

"""
import string
import random


MAX_TRIES = 32767


def generate_id(size=6):
    """Generate random character string of specified size.

    Uses digits, upper- and lower-case letters.
    
    """
    chars=string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for x in range(size))


class Client:
    """Container class for client pNum, user name, group number."""
    def __init__(self, name='anon'):
        self.name = name
        self.guid = None #to be implemented
        self.pNum = None
        self.group = None
        

class ClientManager:
    """Provide mapping functions for Clients with respect to the game engine.

    self.clients is a dictionary of lists, keyed by client guid (str).

    self.groups is a dictionary, keyed by game id (int). The value of each
    group is a dict(guid, Client) of clients that are in the group.
    
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
        self.clients[client].group = group
        self.clients[client].pNum = pNum 

        # Add client to group's info
        self.groups[group][pNum] = client

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
               
        self.clients[guid] = Client(name)
        
        return guid

    def create_group(self):
        """Create new group and return group ID."""
        try:
            last_group = max(self.groups.keys())
        except ValueError:
            last_group = -1

        ident = last_group + 1      # Groups are sequentially numbered.
        self.groups[ident] = {}     # client IDs will be added to this dict

        return ident

    def del_client(self, ident):
        """Delete client and remove from its group (if applicable).

        ident (str): guid for client

        """
        try:
            group = self.clients[ident].group
            del self.clients[ident]

        except KeyError:
            raise KeyError("Client {0} does not exist.".format(ident))

        if group is not None:
            try:
                self.groups[group].remove(ident)
            except KeyError:
                raise KeyError("Group {0} does not exist.".format(group))

    def del_group(self, group_id):
        """Delete group and clear group assignments of associated clients.

        group_id (int): id for group

        """
        try:
            for client in self.groups[group_id]:
                client.group = None

            del self.groups[group_id]
        except KeyError:
            raise KeyError("Group {0} does not exist.".format(group_id))

    def get_client_by_player_num(self, group_id, pNum):
        """Return client guid of player pNum from group.

        group_id (int): id for group
        pNum (int): local player num w/in group

        """
        try:
            group = self.groups[group_id]
        except KeyError:
            raise KeyError("No group with group_id {0} found.".format(group_id))

        try:
            return group[pNum]
        except KeyError:
            return None

    def get_client_info(self, client):
        """Return group_id, playerNum for client.

        client (str): guid of client

        """
        try:
            group = self.clients[client].group
            pNum = self.clients[client].pNum 
            return group, pNum
        except KeyError:
            raise KeyError("Client {0} does not exist.".format(client))

    def get_clients_in_group(self, group_id):
        """Return list of client guids associated with group.

        group_id (int): id for group

        """
        try:
            return self.groups[group_id].values()
        except KeyError:
            raise KeyError("Group {0} does not exist.".format(group_id))
        
    def get_group_by_client(self, client):
        """Return group that contains client.

        client (str): guid of client

        """
        try:
            return self.clients[client].group
        except KeyError:
            raise KeyError("Client {0} does not exist.".format(client))

    def get_player_num_by_client(self, client):
        """Return playerNum for client.

        client (str): guid of client

        """
        try:
            return self.clients[client].pNum 
        except KeyError:
            raise KeyError("Client {0} does not exist.".format(client))
    
    def get_player_names_in_group(self, group):
        """Return dict of player num & name for clients in group.
        
        group (int): group id
        
        """
        players = {} # Key = pNum, value = name
        try:
            client_guids = self.groups[group].values()
            for c in client_guids:
                pNum = self.clients[c].pNum 
                name = self.clients[c].name
                players[pNum] = name
            
            return players
        
        except KeyError:
            return "Cannot get player numbers from Group {0}".format(group)

    def get_player_nums_in_group(self, group):
        """Return list of player numbers of clients in group.

        group (int): group id

        """
        try:
            return self.groups[group].keys()
        except KeyError:
            return "Cannot get player numbers from Group {0}".format(group)

