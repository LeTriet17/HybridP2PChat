# /usr/bin/env python3
import socket
import sys
import os
import pickle
import signal
import datetime
from threading import *
import time
import tqdm

# Note: We declare here the server descriptor, the log file, our server descriptor to be "global variables"
#      and that these can be accessed by the CTRL + C handler and the connection 
#      can be closed correctly(the log file too). This can be done with POO in a cleaner way
#      but I do not have enough time to do it, it is as future improvement for the holidays :) ,
#      let's say that this is the version: P2PChatPy v1.0
#
#   For more info: github.com/davidcawork

# Global vars
BUFFER_SIZE = 2  # send 4096 bytes each time step
# To track stats
proto_msg_sent = 0
proto_msg_rcv = 0
msg_sent = 0
msg_rcv = 0
cmd_used = 0
filename = None
filesize = None
SEND_SUCCESS = None
# Track all msg
msg_history = []

# Peer list
peer_list = []
my_id_peer = None

# To track all readable ways
ways_to_rd = []

# Active_conn
active_conn = []
active_conn_sock = []
# PROTOCOL MSGs
P2P_CHAT_PY_PROTOCOL_HI = 'ChatPy_Hi'
P2P_CHAT_PY_PROTOCOL_HI_ACK = 'ChatPy_Hi_Ack'
P2P_CHAT_PY_PROTOCOL_BYE = 'ChatPy_Bye'
P2P_CHAT_PY_PROTOCOL_BYE_ACK = 'ChatPy_Bye_Ack'
P2P_CHAT_PY_PROTOCOL_UPDATE = 'ChatPy_Update'
P2P_CHAT_PY_PROTOCOL_UPDATE_ACK = 'ChatPy_Update_Ack'
P2P_CHAT_PY_PROTOCOL_CONN = 'ChatPy_Conn'
P2P_CHAT_PY_PROTOCOL_CONN_ACK = 'ChatPy_Conn_Ack'
P2P_CHAT_PY_PROTOCOL_DIS = 'ChatPy_Dis'
P2P_CHAT_PY_PROTOCOL_DIS_ACK = 'ChatPy_Dis_Ack'
P2P_CHAT_PY_PROTOCOL_MSG = 'ChatPy_Msg'
P2P_CHAT_PY_PROTOCOL_FILE_BEGIN = 'ChatPy_File_Begin'
P2P_CHAT_PY_PROTOCOL_FILE_BEGIN_ACK = 'ChatPy_File_Begin_Ack'
P2P_CHAT_PY_PROTOCOL_FILE = 'ChatPy_File'
P2P_CHAT_PY_PROTOCOL_FILE_ACK = 'ChatPy_File_Ack'

# MACROS
MAX_MSG_SAVED = 20

# We parse the info to be able to connect to the p2p_server
name = sys.argv[1]
our_port = int(sys.argv[2])
p2p_server_addr = sys.argv[3]
p2p_server_port = int(sys.argv[4])

# To connect with our server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.connect((p2p_server_addr, p2p_server_port))

# To bind our listen port
ours_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ours_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
ours_server.bind(('', our_port))
ours_server.listen(5)

path = os.getcwd()
file_write = 'write'


# To log all msg
def create_logs():
    isLogDirCreate = False
    list_dir = os.listdir(path)
    LogDir = 'logs'
    for files in list_dir:
        if files == LogDir:
            try:
                isLogDirCreate = True
                log_file = open(path + '/' + LogDir + '/log_' + name + '_' + current_time.strftime('%Y-%m-%d') + '.txt',
                                'w')
            except:
                print('Error: cannot create log files: ' + path + '/' + LogDir + '/log_' +
                      name + '_' + current_time.strftime('%Y-%m-%d') + '.txt')

    if not isLogDirCreate:
        os.mkdir(path + '/' + LogDir)
        try:
            log_file = open(path + '/' + LogDir + '/log_' + name + '_' + current_time.strftime('%Y-%m-%d') + '.txt',
                            'w')
        except:
            print('Error: cannot create log files: ' + path + '/' + LogDir + '/log_'
                  + name + '_' + current_time.strftime('%Y-%m-%d') + '.txt')

    return log_file


# Just for logs
current_time = datetime.datetime.now()
logs = create_logs()


# Handler CTRL+C - Close connection with server
def signal_handler(signum, frame):
    server.sendall(pickle.dumps([P2P_CHAT_PY_PROTOCOL_BYE, [name, our_port], my_id_peer]))
    for conn in active_conn:
        (get_sockpeer_element(conn[3])).sendall(
            pickle.dumps([P2P_CHAT_PY_PROTOCOL_DIS, get_peer_element(my_id_peer)]))

    time.sleep(1)
    logs.close()
    server.close()
    ours_server.close()
    print('\n\nGoodbye!\n')
    sys.exit(0)


# to get cmd written
def is_command(msg, str_cmd):
    return msg.count(str_cmd)


# To print /help cmd
def print_help():
    sys.stdout.flush()
    os.system('clear')
    print('Hi ' + name + ' !\n\n')
    print('These are the commands that you can use:\n')
    print('\t/help\t\tTo consult the commands and guides for using the chat')
    print('\t/quit\t\tTo exit, it close all connections')
    print('\t/timeup\t\tTo get the time you have connected in the chat')
    print('\t/stats\t\tTo get statistics about your activity in the chat')
    print('\t/update\t\tTo update your peer list')
    print('\t/showpeers\tTo show your peers table')
    print('\t/showconn\tTo show your current active connections')
    print('\t/conn [id]\tTo connect with your peers')
    print('\t/dis  [id]\tTo disconnect with your peers')
    print('\t/msg\t\tTo send a msg to some connected peer')
    print('\t\t\tUsage: /msg [id] @messsage\n\n\t\t\tExample: /msg 1 @Hi everyone! :)')
    print('\t/send_file [id] [filename]\t To send file with your peer')
    input("Press Enter to continue...")
    os.system('clear')


# To print msg_history
def print_msgs():
    sys.stdout.flush()
    os.system('clear')
    for msg in msg_history:
        print(msg)


# To manege msg's
def add_to_msgHistory(msg):
    if len(msg_history) == MAX_MSG_SAVED:
        msg_history.pop(0)

    msg_history.append(msg)


# To get time up in the multichat
def timeup_cmd():
    os.system('clear')
    print('Hi ' + name + ' !\n\n')
    time_b = datetime.datetime.now()
    print('You have ' + str(time_b - time_init) + ' time in the chat n.n\n\n\n')
    input("Press Enter to continue...")
    os.system('clear')


# To get our stats :)
def stats_cmd():
    os.system('clear')
    print('Hi ' + name + ' !\n\n')
    time_b = datetime.datetime.now()
    print('Your stats in the multichat:\n')
    print('1.\t Msg sent     : ' + str(msg_sent))
    print('2.\t Msg rcv      : ' + str(msg_rcv))
    print('3.\t Commands used: ' + str(cmd_used))
    print('4.\t msg_History  : ' + str(len(msg_history)))
    print('5.\t Time up      : ' + str(time_b - time_init) + '\n\n')

    input("Press Enter to continue...")
    os.system('clear')


# To print peer table
def print_peer_table():
    os.system('clear')
    print('Hi ' + name + ' !\n\n')
    print('\t\t-- Peer table --\n')
    for peer in peer_list:
        print('+ Name: ' + peer[0] + '\t | Port: ' + str(peer[1]) + ' | Ip: ' + peer[2] + ' | Id_peer: ' + str(peer[3]))
    input("\n\n\nPress Enter to continue...")
    os.system('clear')


# To print active connections table
def print_conn_table():
    os.system('clear')
    print('Hi ' + name + ' !\n\n')
    print('\t\t-- Active connections table --\n')
    for peer in active_conn:
        print('+ Name: ' + peer[0] + '\t | Port: ' + str(peer[1]) + ' | Ip: ' + peer[2] + ' | Id_peer: ' + str(peer[3]))
    input("\n\n\nPress Enter to continue...")
    os.system('clear')


# To get some peer elemnet from peer_list
def get_peer_element(my_peer_id):
    for peer in peer_list:
        if peer[3] is my_peer_id:
            return peer


# To get id_peer from some command
def getPeerId(msg):
    try:
        return int(msg.split(' ')[1])
    except:
        return 0


# To check  if one id_peer is already connected
def is_already_Connected(id_peer):
    for conn in active_conn:
        if conn[3] is id_peer:
            return True

    return False


# To get socket descriptor from active connections
def get_sockpeer_element(id_to_find):
    for conn in active_conn_sock:
        if conn[0][3] is id_to_find:
            return conn[1]


# To get msg from /msg command
def get_msg_to_send(msg):
    return msg.split('@')[1]


def thread_server():
    while True:

        try:
            data = pickle.loads(server.recv(1024))
            if data:
                global peer_list
                global my_id_peer
                if data[0] == P2P_CHAT_PY_PROTOCOL_HI_ACK:

                    # We got the peer_list
                    peer_list = data[1]
                    my_id_peer = data[2]
                    now = datetime.datetime.now()
                    os.system('clear')
                    msg_history.append(
                        '[' + now.strftime('%H:%M:%S') + '] The list of peers was received correctly, ' + str(
                            len(peer_list)) + ' total active peers')
                    print_msgs()

                elif data[0] == P2P_CHAT_PY_PROTOCOL_BYE_ACK:

                    logs.close()
                    server.close()
                    ours_server.close()
                    # Cerrar con lod demas chats

                    now = datetime.datetime.now()
                    msg_history.append('[' + now.strftime('%H:%M:%S') + '] Closing all connections ...')
                    print_msgs()
                    print('\n\nGoodbye ' + name + '!\n')
                    input("Press Enter to continue...")
                    sys.exit(0)

                elif data[0] == P2P_CHAT_PY_PROTOCOL_UPDATE_ACK:
                    # We updated the peer_list
                    peer_list = data[1]
                    now = datetime.datetime.now()
                    os.system('clear')
                    msg_history.append(
                        '[' + now.strftime('%H:%M:%S') + '] The list of peers was updated correctly, ' + str(
                            len(peer_list)) + ' total active peers')
                    print_msgs()

            else:
                logs.close()
                server.close()
                ours_server.close()
                sys.exit(0)
        except:
            logs.close()
            server.close()
            ours_server.close()
            sys.exit(0)


def thread_our_server():
    while True:

        try:
            global ways_to_rd
            conn, addr = ours_server.accept()
            ways_to_rd.append(conn)
        except:
            logs.close()
            server.close()
            ours_server.close()
            return


def thread_input():
    # global cmd_used, proto_msg_sent, msg_sent, active_conn, active_conn_sock,
    global cmd_used, proto_msg_sent, msg_sent, peer_list, ways_to_rd, active_conn, my_id_peer

    while True:

        msg = input('Enter your command: ')
        now = datetime.datetime.now()

        if is_command(msg, '/quit'):
            # To quit the multichat
            os.system('clear')
            server.sendall(pickle.dumps([P2P_CHAT_PY_PROTOCOL_BYE, [name, our_port], my_id_peer]))

            for conn in active_conn:
                (get_sockpeer_element(conn[3])).sendall(
                    pickle.dumps([P2P_CHAT_PY_PROTOCOL_DIS, get_peer_element(my_id_peer)]))
            sys.exit(0)

        elif is_command(msg, '/update'):
            # Request update to p2p2 server
            cmd_used += 1
            proto_msg_sent += 1
            os.system('clear')
            server.sendall(pickle.dumps([P2P_CHAT_PY_PROTOCOL_UPDATE, [name, our_port], my_id_peer]))
            proto_msg_sent += 1

        elif is_command(msg, '/help'):
            # To print help msg
            cmd_used += 1
            print_help()
            print_msgs()

        elif is_command(msg, '/conn'):
            # To connect with someone
            cmd_used += 1
            proto_msg_sent += 1

            id_to_conn = getPeerId(msg)

            if not is_already_Connected(id_to_conn) and id_to_conn:
                try:
                    peer_to_conn = get_peer_element(id_to_conn)

                    msg_history.append(
                        '[' + now.strftime('%H:%M:%S') + ']' + str(my_id_peer) + ' Connecting with ' + str(
                            id_to_conn) + ' ...')

                    aux_peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    aux_peer.connect((peer_to_conn[2], peer_to_conn[1]))
                    ways_to_rd.append(aux_peer)

                    time.sleep(1)
                    aux_peer.sendall(
                        pickle.dumps([P2P_CHAT_PY_PROTOCOL_CONN, get_peer_element(my_id_peer)]))
                except:
                    msg_history.append(
                        '[' + now.strftime('%H:%M:%S') + '] Id_peer: ' + str(id_to_conn) + ' not found ...')

            else:
                msg_history.append('[' + now.strftime('%H:%M:%S') + '] Id_peer: ' + str(
                    id_to_conn) + ' already in use...')
            print_msgs()

        elif is_command(msg, '/dis'):
            # To disconnect with someone
            cmd_used += 1
            proto_msg_sent += 1
            peer_to_dis = []

            id_to_dis = getPeerId(msg)
            if is_already_Connected(id_to_dis):

                try:
                    aux_peer = get_sockpeer_element(id_to_dis)
                    peer_to_dis = get_peer_element(id_to_dis)
                    msg_history.append(
                        '[' + now.strftime('%H:%M:%S') + '] Disconnecting with ' + peer_to_dis[0] + ' ...')

                    time.sleep(1)
                    aux_peer.sendall(
                        pickle.dumps([P2P_CHAT_PY_PROTOCOL_DIS, get_peer_element(my_id_peer)]))
                except:
                    msg_history.append(
                        '[' + now.strftime('%H:%M:%S') + '] Id_peer: ' + peer_to_dis[0] + ' not found ...')



            else:
                msg_history.append('[' + now.strftime('%H:%M:%S') + '] Id_peer: ' + str(
                    id_to_dis) + ' is not in active connections ...')
            print_msgs()


        elif is_command(msg, '/msg'):
            # To communicate with some peers, or single one
            # /msg id @msg
            cmd_used += 1
            proto_msg_sent += 1
            msg_sent += 1

            msg_to_send = get_msg_to_send(msg)

            try:
                id_peer_to_send = getPeerId(msg)
                if is_already_Connected(id_peer_to_send):
                    peer_to_send = get_sockpeer_element(id_peer_to_send)

                    peer_to_send.sendall(pickle.dumps(
                        [P2P_CHAT_PY_PROTOCOL_MSG, get_peer_element(my_id_peer), msg_to_send]))

                    msg_history.append(
                        '[' + now.strftime('%H:%M:%S') + '] You@' + get_peer_element(my_id_peer)[
                            2] + ' > ' + msg_to_send)
                    logs.write(
                        '[' + now.strftime('%H:%M:%S') + '] You@' + get_peer_element(my_id_peer)[
                            2] + ' > ' + msg_to_send + '\n')
                else:
                    msg_history.append(
                        '[' + now.strftime('%H:%M:%S') + '] Id_peer: ' + str(id_peer_to_send) + ' not found ...')
            except:
                msg_history.append('[' + now.strftime('%H:%M:%S') + '] Invalid id_peer ...')

            print_msgs()
        elif is_command(msg, '/send_file'):
            global filename, filesize

            cmd_used += 1
            proto_msg_sent += 1
            msg_sent += 1
            id_peer_to_send = int(msg.split(' ')[1])
            filename = msg.split(' ')[2]
            # the name of file we want to send, make sure it exists
            # get the file size
            filesize = os.path.getsize(filename)
            # try:
            if is_already_Connected(id_peer_to_send):
                peer_to_send = get_sockpeer_element(id_peer_to_send)

                peer_to_send.sendall(pickle.dumps(
                    [P2P_CHAT_PY_PROTOCOL_FILE_BEGIN, get_peer_element(my_id_peer), filename, filesize]))

                msg_history.append(
                    '[' + now.strftime('%H:%M:%S') + '] You@' + get_peer_element(my_id_peer)[
                        2] + ' > ' + 'Sending file to ' + str(id_peer_to_send) + 'with file size' + str(
                        filesize) + ' ' + path + '/' + filename)
                # start sending the file
                progress = tqdm.tqdm(range(filesize), f"Sending {filename}", unit="B", unit_scale=True,
                                     unit_divisor=1024)
                with open(path + '/' + filename, "rb") as f:
                    bytes_read = f.read(BUFFER_SIZE)
                    while bytes_read:
                        peer_to_send.sendall(bytes_read)
                        # update the progress bar
                        progress.update(len(bytes_read))
                        bytes_read = f.read(BUFFER_SIZE)
                        time.sleep(1)

            else:
                msg_history.append(
                    '[' + now.strftime('%H:%M:%S') + '] Id_peer: ' + str(id_peer_to_send) + ' not found ...')
            # except:
            #     msg_history.append('[' + now.strftime('%H:%M:%S') + '] Invalid id_peer ...')

            print_msgs()
        elif is_command(msg, '/showpeers'):
            # To print peer's table
            cmd_used += 1
            print_peer_table()
            print_msgs()

        elif is_command(msg, '/showconn'):
            # To print active connections table
            cmd_used += 1
            print_conn_table()
            print_msgs()

        elif is_command(msg, '/timeup'):
            # To print time up in the multichat
            cmd_used += 1
            timeup_cmd()
            print_msgs()

        elif is_command(msg, '/stats'):
            # To print our stats in the multichat
            cmd_used += 1
            stats_cmd()
            print_msgs()
        else:
            # To support non cmd data
            now = datetime.datetime.now()
            add_to_msgHistory('[' + now.strftime('%H:%M:%S') + '] You: ' + msg)
            print_msgs()
            logs.write('[' + now.strftime('%H:%M:%S') + '] You: ' + msg + '\n')
            return


def thread_peer():
    while True:

        global proto_msg_rcv, msg_rcv, ways_to_rd
        global filename, filesize

        now = datetime.datetime.now()

        for peer in ways_to_rd:
            global active_conn, active_conn_sock, SEND_SUCCESS
            # We only want to check our peers
            # if peer is not server and peer is not ours_server and peer is not socket.socket():
            if peer != server and peer != ours_server:
                data = pickle.loads(peer.recv(1024))
                if data:
                    if data[0] == P2P_CHAT_PY_PROTOCOL_CONN:
                        # To manage incoming connection
                        sock_and_conn = []
                        active_conn.append(data[1])
                        sock_and_conn.append(data[1])
                        sock_and_conn.append(peer)
                        active_conn_sock.append(sock_and_conn)
                        peer.sendall(pickle.dumps(
                            [P2P_CHAT_PY_PROTOCOL_CONN_ACK, get_peer_element(my_id_peer)]))
                        add_to_msgHistory('[' + now.strftime('%H:%M:%S') + '] ' + data[1][
                            0] + ' has connected with you ...')
                        print_msgs()
                        proto_msg_rcv += 1

                    elif data[0] == P2P_CHAT_PY_PROTOCOL_CONN_ACK:
                        # To handle conn ack
                        sock_and_conn = []
                        active_conn.append(data[1])
                        sock_and_conn.append(data[1])
                        sock_and_conn.append(peer)
                        active_conn_sock.append(sock_and_conn)
                        now = datetime.datetime.now()
                        add_to_msgHistory(
                            '[' + now.strftime('%H:%M:%S') + '] Connection accepted')
                        time.sleep(1)
                        print_msgs()
                        proto_msg_rcv += 1
                    elif data[0] == P2P_CHAT_PY_PROTOCOL_FILE_BEGIN:
                        filename = data[2]
                        filesize = data[3]
                        time.sleep(2)
                        total_sent = 0
                        # start receiving the file from the socket
                        # and writing to the file stream
                        progress = tqdm.tqdm(range(filesize), f"Receiving {filename}", unit="B", unit_scale=True,
                                             unit_divisor=1024)
                        with open(path + '/' + file_write + '/' + 'test.csv', "wb") as f:
                            # read 1024 bytes from the socket (receive)
                            bytes_read = peer.recv(BUFFER_SIZE)
                            total_sent += BUFFER_SIZE
                            while bytes_read:
                                f.write(bytes_read)
                                # update the progress bar
                                progress.update(len(bytes_read))
                                if total_sent >= filesize:
                                    break
                                bytes_read = peer.recv(BUFFER_SIZE)
                                total_sent += len(bytes_read)

                            msg_history.append('File sending is done')
                            print_msgs()


                    elif data[0] == P2P_CHAT_PY_PROTOCOL_DIS:
                        # To manage incoming disconnection
                        sock_and_conn_aux = []
                        active_conn.remove(data[1])
                        sock_and_conn_aux.append(data[1])
                        sock_and_conn_aux.append(peer)
                        active_conn_sock.remove(sock_and_conn_aux)
                        peer.sendall(pickle.dumps(
                            [P2P_CHAT_PY_PROTOCOL_DIS_ACK, get_peer_element(my_id_peer)]))
                        ways_to_rd.remove(peer)
                        now = datetime.datetime.now()
                        msg_history.append('[' + now.strftime('%H:%M:%S') + '] ' + data[1][
                            0] + ' is no longer connected to you ...')
                        print_msgs()
                        proto_msg_rcv += 1

                    elif data[0] == P2P_CHAT_PY_PROTOCOL_DIS_ACK:
                        # To handle disconnection ackno.
                        sock_and_conn_aux = []
                        active_conn.remove(data[1])
                        sock_and_conn_aux.append(data[1])
                        sock_and_conn_aux.append(peer)
                        active_conn_sock.remove(sock_and_conn_aux)
                        ways_to_rd.remove(peer)
                        peer.close()
                        now = datetime.datetime.now()
                        msg_history.append(
                            '[' + now.strftime('%H:%M:%S') + '] Disconnected from ' + data[1][0] + ' ...')
                        time.sleep(1)
                        print_msgs()
                        proto_msg_rcv += 1

                    elif data[0] == P2P_CHAT_PY_PROTOCOL_MSG:
                        # To handle incoming msg, just print it and log it
                        now = datetime.datetime.now()
                        msg_history.append(
                            '[' + now.strftime('%H:%M:%S') + '] ' + data[1][0] + '@' + data[1][2] + ' > ' +
                            data[2])
                        logs.write(
                            '[' + now.strftime('%H:%M:%S') + '] ' + data[1][0] + '@' + data[1][2] + ' > ' +
                            data[2] + '\n')
                        print_msgs()
                        proto_msg_rcv += 1
                        msg_rcv += 1
                else:
                    # If no data
                    ways_to_rd.remove(peer)
                    peer.close()
                    return


if __name__ == "__main__":

    # Check argv's
    if len(sys.argv) != 5:
        print('Error: usage: ./' + sys.argv[0] + ' <username> <your_listen_port> <IP_P2P_server> <Port>')
        sys.exit(0)
    else:
        # Let's to prepare the CTRL + C signal to handle it and be able  to close the connection

        # Track time up in the multichat
        time_init = datetime.datetime.now()

        # Say Hi to p2p2 server
        print('Connecting to p2p server...')
        time.sleep(2)
        server.sendall(pickle.dumps([P2P_CHAT_PY_PROTOCOL_HI, [name, our_port]]))
        proto_msg_sent += 1

        # P2P server communication protocol
        server_listen = Thread(target=thread_server)
        server_listen.start()
        # Our server, to accept incoming connections from peers
        # Accept user to chat with him
        ours_server_listen = Thread(target=thread_our_server)
        # Stdin event
        peer_listen = Thread(target=thread_peer)

        # To handle events from peers
        event_listen = Thread(target=thread_input)
        event_listen.start()
        ours_server_listen.start()
        peer_listen.start()
