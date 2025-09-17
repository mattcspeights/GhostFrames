import select
import socket
import sys
import time

HOST = '127.0.0.1'
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.setblocking(False) # non-blocking allows us to do other tasks while waiting for data
    s.connect((HOST, PORT))

    # s.sendto(b"Ping", (HOST, PORT))
    # data, _ = s.recvfrom(1024)
    # print(f"Got: {data}")

    while True:
        readable, _, _ = select.select([s, sys.stdin], [], [], 1.0)
        if readable:
            if s in readable:
                # message from server
                data, addr = s.recvfrom(1024)
                print(f'{addr}: {data}')
            elif sys.stdin in readable:
                # message to send from terminal
                user_input = sys.stdin.readline().strip()
                if user_input:
                    s.sendto(user_input.encode(), (HOST, PORT))
                    print(f'Sent: {user_input}')
        else:
            print('No data received, doing other tasks...')
