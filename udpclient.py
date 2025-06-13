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

        

    def fetch_single_file(self, file_name):
        """单个文件完整下载流程"""
        print(f"[客户端操作] 开始下载文件: {file_name}")
        
        # 发送下载请求并获取响应
        download_cmd = f"DOWNLOAD {file_name}"
        server_reply = self.communicate_with_server(download_cmd, self.server_address)
        if not server_reply:
            print(f"[客户端错误] 下载失败: 未收到服务器响应")
            return
        
           # 响应结果解析
        if server_reply.startswith("ERR"):
            print(f"[客户端错误] 服务器返回错误: {server_reply}")
            return
        if not server_reply.startswith("OK"):
            print(f"[客户端错误] 未知响应格式: {server_reply}")
            return
        
        try:
            # 提取文件大小和数据端口
            size_result = re.search(r"SIZE (\d+)", server_reply)
            port_result = re.search(r"PORT (\d+)", server_reply)
            if not size_result or not port_result:
                print(f"[客户端错误] 响应格式异常: {server_reply}")
                return
            
            file_total_size = int(size_result.group(1))
            data_transfer_port = int(port_result.group(1))
            data_address = (self.server_host, data_transfer_port)
            print(f"[客户端信息] 文件大小: {file_total_size} 字节，数据端口: {data_transfer_port}")

            # 文件分块下载逻辑
            with open(file_name, 'wb') as file_writer:
                downloaded_bytes = 0
                chunk_start = 0
                chunk_size = 1000  # 与服务端保持一致的分块大小
                while downloaded_bytes < file_total_size:
                    chunk_end = min(chunk_start + chunk_size - 1, file_total_size - 1)
                    # 构造数据块请求
                    block_request = f"FILE {file_name} GET {chunk_start} {chunk_end}"
                    block_reply = self.communicate_with_server(block_request, data_address)
                    
                    if not block_reply:
                        print(f"[客户端错误] 数据块请求失败: 起始{chunk_start}, 结束{chunk_end}")
                        break

                    # 解析数据响应
                    if not block_reply.startswith(f"FILE {file_name} OK"):
                        print(f"[客户端错误] 无效数据响应: {block_reply}")
                        continue
                    
                    # 提取并解码文件数据
                    data_match = re.search(r"DATA (.+)$", block_reply, re.DOTALL)
                    if not data_match:
                        print(f"[客户端错误] 数据格式错误: {block_reply}")
                        continue
                    
                    base64_encoded = data_match.group(1)
                    try:
                        decoded_data = base64.b64decode(base64_encoded)
                        file_writer.write(decoded_data)
                        downloaded_bytes += len(decoded_data)
        
        
        