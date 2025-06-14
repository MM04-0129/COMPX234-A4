import socket
import os
import base64
import threading
import random
import time
import re

ORT_RANGE_START = 50000
PORT_RANGE_END = 51000
used_ports = set()

class ClientHandler(threading.Thread):
    def __init__(self, client_addr, filename, server_port):
        threading.Thread.__init__(self)
        self.client_addr = client_addr  # (ip, port)
        self.filename = filename
        self.server_port = server_port
        self.data_port = self.get_free_port()
        self.data_socket = None

    def get_free_port(self):
        while True:
            port = random.randint(PORT_RANGE_START, PORT_RANGE_END)
            if port not in used_ports:
                used_ports.add(port)
                return port

    def run(self):
        try:
            if not os.path.exists(self.filename):
                response = f"ERR {self.filename} NOT_FOUND"
                self.send_response(response)
                return

            file_size = os.path.getsize(self.filename)
            response = f"OK {self.filename} SIZE {file_size} PORT {self.data_port}"
            self.send_response(response)

            self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.data_socket.bind(('0.0.0.0', self.data_port))
            print(f"Data socket started on port {self.data_port}")

            with open(self.filename, 'rb') as f:
                while True:
                    request, client_data_addr = self.data_socket.recvfrom(4096)
                    request = request.decode('utf-8')
                    if request.startswith(f"FILE {self.filename} CLOSE"):
                        close_response = f"FILE {self.filename} CLOSE_OK"
                        self.data_socket.sendto(close_response.encode('utf-8'), client_data_addr)
                        break
                    # 解析 FILE GET START END
                    m = re.match(rf"FILE {re.escape(self.filename)} GET (\d+) (\d+)", request)
                    if m:
                        start, end = int(m.group(1)), int(m.group(2))
                        f.seek(start)
                        data = f.read(end - start)
                        base64_data = base64.b64encode(data).decode('utf-8')
                        response = f"FILE {self.filename} OK START {start} END {end} DATA {base64_data}"
                        self.data_socket.sendto(response.encode('utf-8'), client_data_addr)
        except Exception as e:
            print(f"Error in client handler: {e}")
        finally:
            if self.data_socket:
                self.data_socket.close()
            used_ports.discard(self.data_port)

    def send_response(self, response):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.sendto(response.encode('utf-8'), self.client_addr)
        server_socket.close()        

def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: python udpserver.py <port>")
        sys.exit(1)

    server_port = int(sys.argv[1])
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('0.0.0.0', server_port))
    print(f"Server started on port {server_port}")

    try:
        while True:
            request, client_addr = server_socket.recvfrom(4096)
            request = request.decode('utf-8')
            if request.startswith("DOWNLOAD"):
                filename = request[9:].strip()
                handler = ClientHandler(client_addr, filename, server_port)
                handler.start()
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
    
