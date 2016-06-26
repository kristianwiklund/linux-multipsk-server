
import ConfigParser
import struct, fcntl, os
import asyncore, socket
import alsaaudio
import threading2
import time

mbuffer = ""
lock = threading2.Lock()
connected = False

# audio

class audioloop(threading2.Thread):
    def __init__(self):
        threading2.Thread.__init__(self)
#        print alsaaudio.cards()
        self.inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL,config.get("Audio","card"))
        self.inp.setchannels(1)
        self.inp.setrate(11025)
        self.inp.setformat(alsaaudio.PCM_FORMAT_U8)        
        self.inp.setperiodsize(500)
        print "Started audio listener"
        self.fnopp = False

    def run(self):
        global mbuffer
        global connected 

        while True:
            time.sleep(0.001) # scheduler
            if connected:
                if not self.fnopp: 
                    print "Starting to send audio"
                    self.fnopp = True

                (l,data) = self.inp.read()
#                print "(sound ) wait for lock..."
                if len(mbuffer) < 65535:
                    lock.acquire()                    
                    mbuffer += data
                #                print "(sound ) storing data... mbuffer="+str(len(mbuffer))
                    lock.release()

#                print "(sound ) done"
#                else:
#                    print "(sound ) mbuffer full - dumping data"


# get and send data

class Handler(asyncore.dispatcher):

    def __init__(self,sock):
        global connected
        asyncore.dispatcher.__init__(self,sock)
#        string = "\1\2\3F\0\1skdjfhkshdkjfkshkfhksdhfkskdfksdkfskdjhfksdhkfhksd"
#	print ":".join("{:02x}".format(ord(c)) for c in string)
#	#self.send(string)
#	self.buffer = string
        

    def writable(self):
        global mbuffer

        lock.acquire()
        status = len(mbuffer)
        lock.release()
        if status>0:
            print "(server) data to send"

        return (status > 0)

    def handle_write(self):
        global mbuffer

        print "(server) wait for lock..."
        lock.acquire()
#        print "(server) copy data..."
        # cut up to 500 bytes from the buffer, then release
        mtb = mbuffer[:500]
        mbuffer = mbuffer[len(mtb):]
#        print "(server) data copied..."
        lock.release()        
#        print "(server) lock released..."

        while True:
            sent = self.send("\1\2\3F\0\0")
            sent = self.send(mtb)
#            print "(server) sending "+str(sent)+" bytes of "+str(len(mtb) )
            mtb = mtb[sent:]
            time.sleep(0.01) # schedule
            if len(mtb)<1:
                break
            
        print "(server) done"

    def handle_read(self):
        self.data = self.recv(1024).strip()
        print ":".join("{:02x}".format(ord(c)) for c in self.data)


class Server(asyncore.dispatcher):

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        global connected
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print 'Incoming connection from %s' % repr(addr)
            handler = Handler(sock)
            connected = True

class serverloop(threading2.Thread):
    def __init__(self):
        threading2.Thread.__init__(self)
        self.server = Server(config.get("Network","host"), int(config.get("Network","port")))
        print "Started server listen: "+config.get("Network","host")+":"+config.get("Network","port")
    def run(self):
        asyncore.loop()
        
    

# -------------- main ---------------
config = ConfigParser.ConfigParser({'port':'3020','host':'0.0.0.0','card':'default'})
config.read('multipsk-server.cfg')
config.add_section("Network")
config.add_section("Audio")

thread1 = audioloop()
thread1.start()

thread2 = serverloop()
thread2.start()
