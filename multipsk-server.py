
import ConfigParser
import struct, fcntl, os
import asyncore, socket
import alsaaudio
import time

# audio

def initaudio():
    
    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL,config.get("Audio","card"))
    inp.setchannels(1)
    inp.setrate(11025)
    inp.setformat(alsaaudio.PCM_FORMAT_U8)        
    inp.setperiodsize(500)
    
    return inp

def readaudio(inp):
    d = inp.read()
    return d


# # get and send data

class Handler(asyncore.dispatcher_with_send):
    
    def __init__(self,sock,audio):
        self.inp = audio
        asyncore.dispatcher_with_send.__init__(self,sock)
	self.buffer = ""
        self.dumdata = True
        self.oktosend = False

    def writable(self):
        if not self.oktosend:
            return False

        (l,data) = readaudio(self.inp)

        if l>0:
#            print "(server) data to send"
            self.buffer += data
#            print str(l)+" new, "+str(len(self.buffer))+" total"
            self.dumdata=True
            return True
        elif len(self.buffer)>0:
            return True
        else:
            if self.dumdata:
                print "kein data! Ja!"
                print l
                self.dumdata=False
            return False

    def handle_write(self):
        sent = self.sendall(self.buffer)
        self.buffer=""

    def handle_read(self):
        self.data = self.recv(1024).strip()
        # command mode:

        while len(self.data)>0:
            cmd = self.data[0:6]
            self.data = self.data[6:]
            # check that it is a command
            hdr = cmd[0:3]
            cmd = cmd[3:6]
            cc = cmd[0]

            if hdr == "\1\2\3":
                print "Command "+cc+" received"
                print ":".join("{:02x}".format(ord(c)) for c in cmd)
                
                if cc=="I": # callsign
                    print "Callsign "+str(len(cmd))
                    cl = ord(cmd[2])
                    print "length "+str(cl)+" "+self.data
                    s = self.data[0:cl]
                    self.data=self.data[cl:]
                    print s
                elif cc=="F": # frame format
                    if cmd[1] == "\0": # rx 11025
                        inp.setrate(11025)
                        inp.setperiodsize(500)
                        print "rx bitrate 11025"
                    elif cmd[1] == "\4":
                        inp.setrate(48000)
                        inp.setperiodsize(2200)
                        print "rx bitrate 48000"

                    if cmd[2] == "\1":
                        print "tx bitrate 5512.5"
                    elif cmd[2] == "\0":
                        print "tx bitrate 11025"
                elif cc == "V": # protocol version
                    if cmd == "V02":
                        print "protocol version 2"
                        self.oktosend=True
class Server(asyncore.dispatcher):

    def __init__(self, host, port,audio):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)
        self.inp = audio

    def handle_accept(self):
        global connected
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print 'Incoming connection from %s' % repr(addr)
            handler = Handler(sock,self.inp)
            connected = True


        
    

# -------------- main ---------------
config = ConfigParser.ConfigParser({'port':'3020','host':'0.0.0.0','card':'default'})
config.read('multipsk-server.cfg')
config.add_section("Network")
config.add_section("Audio")

inp = initaudio()

server = Server(config.get("Network","host"), int(config.get("Network","port")),inp)
print "Started server listen: "+config.get("Network","host")+":"+config.get("Network","port")


asyncore.loop()

