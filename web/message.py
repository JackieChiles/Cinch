#!/usr/bin/python3
"""Message object.


"""
class Message:
    """

    """
    def __init__(self, data, source_key=None, dest_key=None):
        """Create Message with data.

        data (dict): dictionary of all data relevant to Message, including
            source, destination, and message body
        source_key (str): dict key in data that holds data source [optional]
        dest_key (str): dict key in data that holds data destination [optional]
        
        """
        if source_key is not None:
            # Set Message.source and remove from data arg
            self.source = data.pop(source_key, None)

        if dest_key is not None:
            # Set Message.destination and remove from data arg
            self.destination = data.pop(dest_key, None)
        
        self.data = data

    def __repr__(self):
        """Stringify this."""
        print("message")

    
