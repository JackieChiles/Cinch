#!/usr/bin/python3
"""Message object for relaying data between web server and engines."""
class Message:
    def __init__(self, data, target=None, source=None):
        """Create Message with data and routing information.

        Setting a source is optional.

        data (dict): dictionary of all data relevant to Message, including
            source, destination, and message body
        source (str): ID of source of message
        target (str): destination ID for message
        
        """
        assert isinstance(data, dict)
        assert (isinstance(target, str) or target is None)
        
        self.source = source
        self.target = target
        self.data = data

    def __repr__(self):
        """Return descriptive string of Message."""
        return "From: {0}\nTo: {1}\nData: {2}".format(self.source,
                                                      self.target,
                                                      self.data)

