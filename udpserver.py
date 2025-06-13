import socket
import os
import base64
import threading
import random
import time
import re

ORT_RANGE_START = 50000
PORT_RANGE_END = 51000

class ClientHandler(threading.Thread):
    def __init__(self, client_addr, client_port, filename, server_port):
        threading.Thread.__init__(self)
        self.client_addr = client_addr
        self.client_port = client_port
        self.filename = filename
        self.server_port = server_port
        self.data_port = random.randint(PORT_RANGE_START, PORT_RANGE_END)
        self.data_socket = None
        self.file = None