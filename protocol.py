import base64


SERVER_PORT = 5555
#SERVER_IP = "127.0.0.1"
SERVER_IP = "192.168.1.154"
DELIMITER = "|"


def get_analyzed_data(client_socket):
    datasize = client_socket.recv(1)
    if datasize == b"":
        return None
    datasize = datasize.decode()
    while datasize[-1] != DELIMITER:
        datasize += client_socket.recv(1).decode()
    datasize = int(datasize[:-1])
    b64data = b''
    b64data += client_socket.recv(datasize)
    while datasize > len(b64data):
        b64data += client_socket.recv(datasize - len(b64data))
    data = base64.b64decode(b64data)
    return data


def create_message(data):
    if type(data) is str:
        data = data.encode()
    b64data = base64.b64encode(data)
    return f"{len(b64data)}|".encode() + b64data

