#!/usr/bin/python3
"""Message object for relaying data between web server and engines."""
class Message:
    def __init__(self, data, source_key=None, dest_key=None):
        """Create Message with data and routing information.

        data (dict): dictionary of all data relevant to Message, including
            source, destination, and message body
        source_key (str): dict key in data that holds data source [optional]
        dest_key (str): dict key in data that holds data destination list
        
        """
        # Initialize variables in case print() is called on malformed object
        self.source = None
        self.dest_list = None
        self.data = None
        
        if source_key is not None:
            # Set Message.source and remove from data arg
            self.source = data.pop(source_key, None)

        if dest_key is not None:
            # Set Message.destination and remove from data arg
            self.dest_list = data.pop(dest_key, [])
        
        self.data = data

    def __repr__(self):
        """Stringify this."""
        print("From: {0}\nTo: {1}\nData: {3}\n".format(
            self.source, self.dest_list, self.data))
