#!/usr/bin/python3
"""
A collection of functions for parsing Cinch game events into usable data.

Current contents:

process(gid, hNum): Grab all events with the chosen game id (gid) and hand
                   number (hNum) and parse them for addition to the other
                   tables.
"""

import sqlite3
import logging      #Will leave the logging facilities here alone.
import ast

DB_PATH = 'db/cinch.db'
LOG_FILE = 'db/stats.log'
LOGGING_LEVEL = logging.DEBUG
NUM_PLAYERS = 4

def process(gid, hNum):

    # Set up logging.
    logging.basicConfig(filename=LOG_FILE,level=LOGGING_LEVEL)

    # Open the database.
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
  
    # Verify that the destination tables exist. If they don't, add them.
    try:
        c.execute('''select * from hands where hand_id=-1''')
    except sqlite3.OperationalError:
        c.execute('''create table hands (
                         hand_id integer primary key,
                         game_id integer not null,
                         dealer integer,
                         declarer integer,
                         trump integer,
                         high_bid integer,
                         hand_number integer)''')
    try:
        c.execute('''select * from actions where action_id=-1''')
    except sqlite3.OperationalError:
        c.execute('''create table actions (
                         action_id integer primary key,
                         game_id integer not null,
                         hand_id integer not null,
                         pnum integer not null,
                         bid integer,
                         rank integer,
                         suit integer)''')

    # Select all rows from the relevant game/hand combination.
    args = (gid, hNum)
    c.execute('''select eventstring from events where game_id=? and 
              handnumber=? order by event_id''', args)
              
    # Now, extract the event strings. We aren't concerned with players' hands,
    # so it's OK to extract the dictionaries inside the lists (that's what the
    # second [0] subscript is for). New hand records therefore will only have
    # the message as sent to player 0, but the information used by process()
    # is all the same.
    events = []
    for row in c:
        events.append(ast.literal_eval(row[0])[0])

    # Make sure there are an appropriate number of rows.
    if hNum is 1:
        if len(events) is not 41:
            logging.error('Game %s: %s rows found for hand %s; expected 41.',
                          gid, len(events), hNum)
            c.close()
            return
        else:
            events = events[1:] # Remove the game start message.
    else:
        if len(events) is not 40:
            logging.error('Game %s: %s rows found for hand %s; expected 40.',
                          gid, len(events), hNum)
            c.close()
            return
    # Add a row to the hands table with relevant information.        
    try:
        _dealer = (events[0]['actvP'] + 2) % NUM_PLAYERS
            # The 'dlr' key isn't tagged with the right hand number for hands
            # after the first; so here's a clumsy workaround. Another possi-
            # bility is to add a second 'dlr' key in the subsequent message,
            # but it seems best to keep the logging quirks in the logging
            # function.
        _declarer = events[3]['actvP']
        _trump = events[4]['trp']
        _high_bid = max([events[_]['bid'] for _ in range(0,3)])
        _hand_number = hNum
    except KeyError as k:
        logging.error('Game %s, hand %s parsing error: %s', gid, hNum, k)
        c.close()
        return
    c.execute("insert into hands values (NULL,?,?,?,?,?,?)",
              (gid, _dealer, _declarer, _trump, _high_bid,
               _hand_number))
    c.execute("SELECT last_insert_rowid()")
    autogen_hand_id = c.fetchone()[0] # Unpack len-1 tuple to get int

    # Process the 4 bids and 36 plays for the hand.
    for count, row in list(enumerate(events)):
        try:
            _bid = row['bid']
        except KeyError:
            _bid = None
        try:
            _suit = (row['playC']-1)//13
            _rank = row['playC'] - _suit*13 + 1
        except KeyError:
            _suit = None
            _rank = None
            
        if (_bid is None) and (_suit is None) and (_rank is None):
            logging('Game %s, hand %s: No action found on line %s.',
                    gid, hNum, count)
            c.close()
            return
            
        try:
            _pNum = row['actor']
        except KeyError as k:
            logging.error('Game %s, hand %s parsing error: %s', gid, hNum, k)
            c.close()
            return

        c.execute("insert into actions values (NULL,?,?,?,?,?,?)",
                  (gid, autogen_hand_id, _pNum, _bid, _rank, _suit))

    conn.commit()
    c.close()
