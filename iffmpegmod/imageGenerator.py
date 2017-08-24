import subprocess
import config
import os
import shlex
import time
import logging
import atexit
import signals
import readline

class ImageGenerator:
    """ Listens to the <streamId>/input topic for chunks of video data 
        then feeds them to ffmpeg that in turn generates an image
        in the ram directory. Once a new image has been generated 
        this class generates <streamId>/snapshot message.
    """
    def __init__(self, streamId, interval=3):
        
        self.imgfile = config.RAMDISK_DIR + "/%s.jpg" % streamId
        self.sid = streamId
        self.last_mtime = None
        self.subscribed = False
        
        self.vin_r,self.vin_w = os.pipe()
        cmdfmt = "%s -re -loglevel -8 -i pipe:%d -r 1/%d -f image2 -update 1 %s"
        self.cmd = cmdfmt % (config.FFMPEG,self.vin_r,interval,self.imgfile)
        self.si_topic = config.StreamInputTopic(self.sid) 
        self.img_topic = config.ImageTopic(self.sid) 
        self.stop_topic = config.StreamStopTopic(self.sid) 
       
        self.proc = None

    def __del__(self):
        try: 
            os.close(self.vin_r)
            os.close(self.vin_w)
        except:
            pass 

    def feed(self, data):
        """
        Feed data to ffmpeg, allow it to generate an image, send
        the filename of the image if it is a new image and at
        the minimum interval.
        """
        logging.debug("writing chunk to pipe") 
        retval = self.proc.poll()
        if retval:
            logging.error("imageGenerate: ffmpeg crash")
            return 
 
        os.write(self.vin_w,data)
        if os.access(self.imgfile,os.F_OK):
            mtime = os.stat(self.imgfile) 
            logging.info("mtime = %s" % str(mtime))
            if not self.last_mtime or mtime != self.last_mtime:
                signals.publish(self.img_topic, self.imgfile)
                self.last_mtime = mtime
          

    def start(self):
        # listen for data from the streamInput object, route to
        # internal process that generates 
        if not self.subscribed: 
            signals.subscribe(self.si_topic,self.feed)
            signals.subscribe(self.stop_topic,self.stop)
            self.subscribed = True

        if os.access(self.imgfile,os.F_OK):
            os.remove(self.imgfile)
  
        logging.info(self.cmd) 
        self.proc = subprocess.Popen(shlex.split(self.cmd),shell=False)
        atexit.register(self.stop)

    def stop(self):
        if self.proc:
            logging.info("stopping image generator for sid=%s" % self.sid)
            retval = self.proc.poll()
            if not retval: 
                self.proc.kill()
                self.proc.communicate(b'')
            self.proc = None


def onStreamCreate(stream):
    gen = ImageGenerator(stream['streamId'])
    
    





def unittest():
    import sys, time
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG,
        format="%(asctime)s %(message)s"
    )

    sid="test"
    ig = ImageGenerator(sid)
    si_topic = config.StreamInputTopic(sid)
    img_topic = config.ImageTopic(sid)
    def image_ready(filename=""):
        logging.info("++++++++++++ image ready ++++++++++++")   
 
    signals.subscribe(img_topic,image_ready)
    stop_topic = config.StreamStopTopic(sid)        
    ig.start()
    f = open(os.environ['HOME']+"/oceans.mp4")
    while True:
        time.sleep(0.25)
        chunk = f.read(32767) 
        if not chunk or len(chunk) == 0:
            break
         
        #ig.feed(chunk) 
        signals.publish(si_topic,chunk)
    signals.publish(stop_topic)
        

if __name__ == '__main__':
    unittest()



