import socket
import os, sys
import thread
import time, datetime
import struct
from PyQt4.QtGui import *
import SocketServer
from PyQt4.QtCore import *
from PyQt4 import Qt

MESSAGE = ""
UDP_PORT = 9999
OUT_PORT = 5681
FILE_NAME = "/home/javier/Hask_1/myalloc/myalloc.c"
clients = dict()


app = QApplication(sys.argv)
widget = QListWidget()

def getFileList(path):
    fileList = []
    l = os.listdir(path)
    for pth in l:
        fpth = path + "/" + pth
        if os.path.isfile(fpth):
            fileList.append(pth)
    return fileList

class MyTCPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        print "Connection handled"
        with open(FILE_NAME) as f:
            s = f.read()
        msg = struct.pack("!L", 1) + struct.pack("!L", len(s)) + s
        self.request.sendall(msg)

def get_utc():
    return long(time.mktime(datetime.datetime.now().timetuple()))

def convert_string_to_hex_packet(string_packet):
    result_hex_packet = ""
    for i in xrange(len(string_packet)):
        result_hex_packet += ("%02X " % ord(string_packet[i]))
    return result_hex_packet[:-1]

def get_out_string(data):
    if len(data) < 4:
        return ("", "")
    s_len = struct.unpack("!L", data[0:4])[0]
    data = data[4:]
    return (data[0:s_len], data[s_len:])

def threadRecv():
    global clients
    global widget
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', UDP_PORT))
    while True:
        data, addr = sock.recvfrom(8092)
        if len(data) > 4:
            #print "== RECV: %s ==" % convert_string_to_hex_packet(data)
            IP, data = get_out_string(data)
            COMPNAME, data = get_out_string(data)
            if len(data) >= 8:
                SYSTIME = struct.unpack("!Q", data[0:8])[0]
                data = data[8:]
                SURNAME, data = get_out_string(data)
                parity, hport = struct.unpack("!LL", data[0:8])
                if not (IP in clients):
                    widget.addItem(QListWidgetItem(IP))    
                clients[IP] = (COMPNAME, SYSTIME, SURNAME, get_utc(), parity, hport)
                #os.system('clear')
                # print "== LIST (%d clients) ==" % len(clients)
                for _ip in clients.keys():
                    el = clients[_ip]
                    if (el[3] + 6 < get_utc()) or (el[1] > get_utc() + 3600):
                        del clients[_ip]
                        widget.removeItemWidget(QListWidgetItem(_ip))
               #     print "%s:\t%s,\t%s,\t%s,\t %s \t %s" % (_ip, el[0], el[1], el[2], el[4], el[5])

def TCPServerThread():
    server = SocketServer.TCPServer(("", OUT_PORT), MyTCPHandler)
    server.serve_forever()

def TCPClientThread(host_ip):
    global clients
    if (host_ip in clients):
        h_port = clients[host_ip][5]
        parity = clients[host_ip][4]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    
        try:
           sock.connect((host_ip, h_port))
           if parity:
               prefix = sock.recv(8)
               if len(prefix) == 8:
                   tmp , l = struct.unpack("!LL", prefix)
                   data = sock.recv(l)
                   with open('log.txt', 'w') as f:
                       f.write(data)
           else: 
                prefix = sock.recv(4)
                data = ''
                if len(prefix) == 4:
                    amount = struct.unpack("!L", prefix)[0]
                    f = open('log.txt', 'w')
                    for i in range(0, int(amount)):
                        prefix = sock.recv(4)
                        l = struct.unpack("!L", prefix)[0]
                        data = "%s%s%s" % (data, sock.recv(int(l)), '\n')
                    with open("log.txt","w") as f:
                        f.write(data)             
        finally:
           sock.close()    

def BroadCastUDP():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    _IP = socket.gethostbyname(socket.gethostname())
    _COMPNAME = socket.gethostname()
    _SURNAME = "Karpov"
    try:
       while True:
            _SYSTIME = get_utc()
            MESSAGE = struct.pack("!L", len(_IP)) + _IP + struct.pack("!L", len(_COMPNAME)) + _COMPNAME + struct.pack("!Q", _SYSTIME) + struct.pack("!L", len(_SURNAME)) + _SURNAME + struct.pack("!L", 1) + struct.pack("!L", OUT_PORT)
            sock.sendto(MESSAGE, ('<broadcast>', UDP_PORT))
            time.sleep(2)
    finally:
        sock.close()

def clickAction():
    for i in range(widget.count()):
        if widget.item(i).isSelected():
            ip = widget.item(i).text()
            print "Request to %s" % ip
            TCPClientThread("%s" % ip)

def runGUI():
    global app
    global widget
    widget.setSortingEnabled(True)
    widget.clicked.connect(clickAction)
    widget.resize(640, 480)
    widget.show()
    app.exec_()

if __name__ == "__main__":
    thread.start_new_thread(threadRecv, ())
    thread.start_new_thread(TCPServerThread, ())
    thread.start_new_thread(BroadCastUDP, ())
    
    sys.exit(runGUI())
