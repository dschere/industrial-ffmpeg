import fcntl
import os

class nonblockingReadline:
    def __init__(self, fileObj):
        self.fd = fileObj.fileno()
        fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        self.buf = ''

    def readline(self):
        chunk = os.read(self.fd,4096)
        if chunk and len(chunk) > 0:
            self.buf += chunk 
        pos = self.buf.find('\n')
        if pos > -1:
            r = self.buf[:pos]
            self.buf = self.buf[pos+1:]
            return r
  
