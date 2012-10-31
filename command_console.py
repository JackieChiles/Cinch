#!/usr/bin/python3
"""Provide interface for sending commands to live Cinch server."""
from multiprocessing.connection import Client, Listener
from time import sleep

self_address = ('localhost', 8676)
server_address = ('localhost', 8675)


def menu():
    print()
    val = input('$ > ')
    print()
    
    return val

if __name__ == "__main__":
    sleep(0.5) # Allow extra time for Cinch server to prepare
    
    # First, contact waiting server
    conn_out = Client(server_address)

    # Then, listen for first response
    listener = Listener(self_address)
    conn_in = listener.accept()
    print("="*40)
    print("Connection established with Cinch server")
    print()
    print("Typing 'help' is a good start; 'exit' quits the command console.")    

    # Begin menu interface with user
    while True:
        val = menu()
        
        if "exit" == val:
            break
        else:
            conn_out.send(val)
            print(conn_in.recv())
            
            if "halt" == val:
                break # User took server down, so exit here too.
    
    conn_out.close()
    conn_in.close()
    listener.close()
