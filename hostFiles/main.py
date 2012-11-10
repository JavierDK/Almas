#! /usr/bin/python

import socket
import os, sys
import thread
import time, datetime
import struct
from PyQt4.QtGui import *
import SocketServer
from PyQt4.QtCore import *
from PyQt4 import Qt
import hashlib

MESSAGE = ""
MAX_FILES = 15
UDP_PORT = 9999
OUT_PORT = 9999
DIR_NAME = "/home/javier/BisonLab/"
hosts = dict()
curHost = ""

app = QApplication(sys.argv)
widget = QWidget()
hostWidget = QListWidget(widget)
fileWidget = QListWidget(widget)
listBut = QPushButton("LIST", widget)
pullBut = QPushButton("PULL", widget)
pushBut = QPushButton("PUSH", widget)

def incContentID(cont_id):
    return str(int(cont_id) +  1)


def getFileList(path):
    fileList = []
    l = os.listdir(path)
    for pth in l:
        fpth = path + "/" + pth
        if os.path.isfile(fpth):
            fileList.append(pth)
    return fileList

def get_out_string(data):
    if len(data) < 4:
        return ("", "")
    s_len = struct.unpack("!L", data[0:4])[0]
    data = data[4:]
    return (data[0:s_len], data[s_len:])

def get_utc():
    return long(time.mktime(datetime.datetime.now().timetuple()))

def getList(tcp):
    print "LIST"
    fList = getFileList(DIR_NAME)
    msg = struct.pack("!L", len(fList))
    for i in fList:
        with open(DIR_NAME + i) as f:
            h = hashlib.md5()
            h.update(f.read())
            msg = msg + struct.pack("!L", len(h.digest())) + h.digest()
    tcp.request.sendall(msg)

def getGet(tcp):
    print "GET"
    fList = getFileList(DIR_NAME)
    fname = ""
    msg = ""
    data = tcp.request.recv(4)
    length = struct.unpack("!L", data[0:4])[0]
    data = tcp.request.recv(length)
    for i in fList:
        with open(DIR_NAME + i) as f:
            h = hashlib.md5()
            h.update(f.read())
            if (h.digest() == data):
                fname = i
    print fname 
    if fname == "":
        msg = struct.pack("!c", str(0x01))
    else:
        msg = struct.pack("!c", str(0x00))
        f = open(DIR_NAME + fname)
        content = f.read()
        msg = msg + struct.pack("!L", len(content)) + content
    tcp.request.sendall(msg)

def getPut(tcp):
    print "PULL"
    fList = getFileList(DIR_NAME)
    data = tcp.request.recv(4)
    con_len = struct.unpack("!L", data)[0]
    data = tcp.request.recv(con_len)
    if (len(fList) >= MAX_FILES):
        msg = struct.pack("!c", str(0x01))
    else:
        msg = struct.pack("!c", str(0x01))
        h = hashlib.md5()
        h.update(data)
        f = open(DIR_NAME + h.hexdigest(), 'w')
        f.write(data)
    tcp.request.sendall(msg)

class MyTCPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        self.data = self.request.recv(4);
        data = self.data;
        reqType = struct.unpack("!L", data[0:4])[0];
        msg = ""
        if reqType == 0:
            getList(self)
            return    
        if reqType == 1:
            getGet(self)
            self.request.sendall(msg)
        if reqType == 2:
            getPut(self)
            return

def getAlive():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', UDP_PORT))
    while True:
        data, addr = sock.recvfrom(8092)
        changed = False
        if len(data) > 4:
            IP, data = get_out_string(data)
            COMPNAME, data = get_out_string(data)
            CONT_ID, data = get_out_string(data)
            TIME = get_utc();
            if (not IP in hosts.keys()) or (hosts[IP][1] != CONT_ID):
                changed = True
            hosts[IP] = (COMPNAME, CONT_ID, TIME)
        curr_time = get_utc()
        for ip in hosts.keys():
           if curr_time - hosts[ip][2] > 20:
               del hosts[ip]
               changed = True
        if changed:
            print "Refresh"
            for ip in hosts.keys():
                hostWidget.clear()
                s = ip + "\t" + hosts[ip][0] + "\t" + hosts[ip][1]
                hostWidget.addItem(s);
           
                
def TCPServerThread():
    server = SocketServer.TCPServer(("", OUT_PORT), MyTCPHandler)
    server.serve_forever()

def getMD5():
    chsum = hashlib.md5();
    fList = getFileList(DIR_NAME)
    for i in fList:
        s = ""
        chsum.update(i)
        with open(DIR_NAME + i) as fl:
            s = fl.read()
            chsum.update(s)
    return chsum.digest()

def sendAlive():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    _IP = socket.gethostbyname(socket.gethostname())
    _COMPNAME = socket.gethostname()
    md5sum = getMD5()
    cont_id = "0"       
    try:
       while True:
          _SYSTIME = get_utc
          if md5sum != getMD5():
              cont_id = incContentID(cont_id)
              md5sum = getMD5()                
          MESSAGE = struct.pack("!L", len(_IP)) + _IP + struct.pack("!L", len(_COMPNAME)) + _COMPNAME +  struct.pack("!L", len(cont_id)) + cont_id
          sock.sendto(MESSAGE, ('<broadcast>', UDP_PORT))
          time.sleep(10)
    finally:
       sock.close()

def sendList():
    global curHost
    ip = ""
    for i in range(hostWidget.count()):
        if hostWidget.item(i).isSelected():
            ip = str(hostWidget.item(i).text()).split("\t", 1)[0]
            break;
    curHost = ip
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, OUT_PORT))
    msg = struct.pack("!L", 0)
    sock.sendall(msg)
    data = sock.recv(4)
    N = struct.unpack("!L", data)[0]
    fileWidget.clear()
    for i in range(N):
        data = sock.recv(4)
        s_len = struct.unpack("!L", data)[0]
        chsum = sock.recv(s_len)
        fileWidget.addItem(chsum.encode('hex'))
        

def sendGet():
    ip = curHost
    for i in range(fileWidget.count()):
        if fileWidget.item(i).isSelected():
            chsum = str(fileWidget.item(i).text()).decode('hex')
            break;
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, OUT_PORT))
    msg = struct.pack("!L", 1) + struct.pack("!L", len(chsum)) + chsum
    sock.sendall(msg)
    data = sock.recv(1)
    status = struct.unpack("!c", data)[0]
    if status == 1:
        print "Get failed"
        return
    print "Successful Get"
    data = sock.recv(4)
    length = struct.unpack("!L", data)[0]
    data = sock.recv(length)
    f = open(DIR_NAME + chsum.encode('hex'), 'w')
    f.write(data)

def sendPut():
    myIP = socket.gethostbyname(socket.gethostname())
    if curHost != myIP:
        return
    ip = ""
    for i in range(hostWidget.count()):
        if hostWidget.item(i).isSelected():
            ip = str(hostWidget.item(i).text()).split("\t", 1)[0]
            break;
    if ip == "":
        return
    for i in range(fileWidget.count()):
        if fileWidget.item(i).isSelected():
            chsum = str(fileWidget.item(i).text()).decode('hex')
            break;
    fList = getFileList(DIR_NAME)
    fname = ""
    content = ""
    for i in fList:
        with open(DIR_NAME + i) as f:
            h = hashlib.md5()
            s = f.read()
            h.update(s)
            if h.digest() == chsum:
                fname = i
                content = s
    if fname == "":
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, OUT_PORT))
    msg = struct.pack("!L",2) + struct.pack("!L", len(content)) + content
    sock.sendall(msg)
    data = sock.recv(1)
    status = struct.unpack("!c", data)[0]
    if status == 1:
        print "Put failed"
    else:
        print "Succesful Put"
    

def runGUI():
    global app
    global widget
    widget.resize(640, 480)
    hostWidget.setSortingEnabled(True)
    hostWidget.move(0, 20)
    hostWidget.resize(300, 380)
    fileWidget.move(301, 20)
    fileWidget.resize(339, 380)
    listBut.move(10, 410)
    listBut.resize(280, 20)
    listBut.clicked.connect(sendList)
    pullBut.move(310, 410)
    pullBut.resize(320, 20)
    pullBut.clicked.connect(sendGet)
    pushBut.move(310, 440)
    pushBut.resize(320, 20)
    pushBut.clicked.connect(sendPut)
    widget.show()
    app.exec_()

if __name__ == "__main__":
    thread.start_new_thread(sendAlive, ())
    thread.start_new_thread(getAlive, ())
    thread.start_new_thread(TCPServerThread, ())
    
    
    sys.exit(runGUI())
