#!/usr/bin/python3
"""Message object for relaying data between web server and engines."""
class Message:
    def __init__(self, data, source=None, dest_list=None, 
                 source_key=None, dest_key=None):
        """Create Message with data and routing information.

        source and/or dest_list can be passed directly. If done, then the value
        should not be included within data. Otherwise, set source_key and/or
        dest_key and include within data.

        Setting a source is optional.

        data (dict): dictionary of all data relevant to Message, including
            source, destination, and message body
        source (str): ID of source of message
        dest_list (list): list of destinations for message
        source_key (str): dict key in data that holds data source
        dest_key (str): dict key in data that holds data destination list
        
        """
        # Don't allow caller to set both source and source_key
        assert (source is None or source_key is None)

        # Don't allow caller to set both dest_list and dest_key
        assert (dest_list is None or dest_key is None)

        if source is not None:
            self.source = source
        elif source_key is not None:
            # Set Message.source and remove from data
            self.source = data.pop(source_key, None)
        else:
            self.source = None

        if dest_list is not None:
            self.dest_list = dest_list
        else:
            # Set Message.destination and remove from data
            self.dest_list = data.pop(dest_key, [])

        # A destination list must be set for Message
        assert (self.dest_list is not None)
        assert isinstance(self.dest_list, list)
        
        self.data = data

    def __repr__(self):
        """Return descriptive string of Message."""
        return "From: " + str(self.source) + "\nTo: " + str(self.dest_list) \
               + "\nData: " + str(self.data)
