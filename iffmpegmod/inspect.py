#!/usr/bin/env python
"""
Uses ffprobe to inspect a stream to determine the format,frame rate
and quality of the stream.
"""
import shlex
import subprocess
import config
import json
import threading
import os
import select
import time    

def inspect(url):
    cmdfmt = "%s -loglevel -8 -print_format json -show_format -show_streams %s" 
    stdout = os.popen(cmdfmt % (config.FFPROBE,url)).read() 
    return json.loads(stdout)

def async_inspect(url, success, failure, timeout=60):
    cmdfmt = "%s -loglevel -8 -print_format json -show_format -show_streams %s"
    f = os.popen(cmdfmt % (config.FFPROBE,url))
    plist = select.poll()
    plist.register( f.fileno(), select.POLLIN )
    def wait():
        expire = time.time() + timeout
        while expire > time.time():
            for (fd,evt) in plist.poll(1000):
                if evt & select.POLLIN:
                    buf = f.read()
                    success(json.loads(buf))
                    return  
        failure()

    t = threading.Thread( target=wait)
    t.daemon = True
    t.start()        
    

if __name__ == '__main__':
    import sys

    def success(jobj):
        print( json.dumps(jobj,indent=4,sort_keys=True) )
        sys.exit(0)

    def failure():
        print( "timeout" )
        sys.exit(-1) 

    jobj = async_inspect(sys.argv[1], success, failure)
    time.sleep( 70 )

    
