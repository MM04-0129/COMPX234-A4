import socket
import os
import base64
import time
import re
import sys


MAX_RETRIES = 5
INITIAL_TIMEOUT = 1  

class FileDownloadClient:
    def __init__(self, server_host, server_port_num, file_list_location):
        """初始化客户端，配置服务器地址与文件列表路径"""
        self.server_host = server_host
        self.server_port = server_port_num
        self.file_list_path = file_list_location
        # 创建UDP套接字
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (server_host, server_port_num)

    def start_download(self):
        """按文件列表顺序执行批量下载"""
        if not os.path.isfile(self.file_list_path):
            print(f"[客户端提示] 文件列表不存在: {self.file_list_path}")
            return
        
        with open(self.file_list_path, 'r', encoding='utf-8') as file_reader:
            for line in file_reader:
                target_file = line.strip()
                if target_file:
                    self.fetch_single_file(target_file)

