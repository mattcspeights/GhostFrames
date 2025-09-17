import select
import socket
import sys

HOST = '127.0.0.1'
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.bind((HOST, PORT))
    print(f'Server listening on {HOST}:{PORT}')

    s.setblocking(False) # non-blocking allows us to do other tasks while waiting for data

    while True:
        readable, _, _ = select.select([s, sys.stdin], [], [], 1.0)
        if readable:
            if s in readable:
                # message from client
                data, addr = s.recvfrom(1024)
                print(f'{addr}: {data}')
                s.sendto(b'Hello back! You sent me this: "' + data + b'"', addr)
            elif sys.stdin in readable:
                # message to send from terminal
                user_input = sys.stdin.readline().strip()
                if user_input:
                    print(f'Going to send (but dont have addr): {user_input}')
        else:
            print('No data received, doing other tasks...')
