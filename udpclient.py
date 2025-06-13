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
                        # 进度显示逻辑
                        progress_percent = int(downloaded_bytes / file_total_size * 50)
                        progress_bar = '#' * progress_percent + '-' * (50 - progress_percent)
                        print(f"[客户端进度] 下载进度: [{progress_bar}] {downloaded_bytes}/{file_total_size}字节", end='\r')
                    except Exception as decode_err:
                        print(f"[客户端错误] 数据解码失败: {str(decode_err)}")
                        break
                    
                    if chunk_end >= file_total_size - 1:
                        break  # 最后一块数据
                    chunk_start = chunk_end + 1

                print("\n[客户端进度] 下载进度: 100%")
    # 发送关闭连接请求
            close_cmd = f"FILE {file_name} CLOSE"
            close_response = self.communicate_with_server(close_cmd, data_address)
            
            if close_response and close_response.startswith(f"FILE {file_name} CLOSE_OK"):
                print(f"[客户端完成] 下载完成: {file_name}")
            else:
                print(f"[客户端警告] 关闭连接异常，可能未收到确认响应")
                
        except Exception as download_err:
            print(f"[客户端错误] 下载过程异常: {str(download_err)}")
            if os.path.exists(file_name):
                os.remove(file_name)  # 清理不完整文件

    def communicate_with_server(self, msg, target_address):
        """处理与服务器的收发逻辑（含超时重试）"""
        retry_count = 0
        current_timeout = INIT_TIMEOUT
        
        while retry_count <= MAX_RETRY_TIMES:
            try:
                self.udp_socket.settimeout(current_timeout)
                # 发送数据
                self.udp_socket.sendto(msg.encode('utf-8'), target_address)
                
                # 尝试接收响应
                try:
                    response_data, _ = self.udp_socket.recvfrom(65536)
                    if response_data:
                        return response_data.decode('utf-8').strip()
                except socket.timeout:
                    pass  # 超时未收到响应，进入重试流程 
                 # 重试逻辑
                retry_count += 1
                if retry_count > MAX_RETRY_TIMES:
                    print(f"[客户端重试] 达到最大重试次数{MAX_RETRY_TIMES}，当前超时{current_timeout}秒")
                    return None
                
                # 指数退避策略
                current_timeout = min(current_timeout * 2, 32)  # 超时上限32秒
                print(f"[客户端重试] 未收到响应，将在{current_timeout}秒后重试（第{retry_count}次）")
                time.sleep(current_timeout)
                
            except socket.error as socket_err:
                print(f"[客户端错误] 网络操作失败: {str(socket_err)}")
                retry_count += 1
                if retry_count <= MAX_RETRY_TIMES:
                    time.sleep(current_timeout)
                else:
                    return None
        
        return None
                    
def execute_client():
    if len(sys.argv) != 4:
        print("使用方法: python client_script.py <服务器主机名> <服务器端口> <文件列表路径>")
        print("示例: python client_script.py localhost 51234 files.txt")
        sys.exit(1)
    
    server_host = sys.argv[1]
    server_port = int(sys.argv[2])
    file_list = sys.argv[3]
    
    try:
        client = FileDownloadClient(server_host, server_port, file_list)
        client.start_download()
    except Exception as global_err:
        print(f"[客户端崩溃] 程序异常终止: {str(global_err)}")
        sys.exit(1)


if __name__ == "__main__":
    execute_client()                    


            
        
        
        