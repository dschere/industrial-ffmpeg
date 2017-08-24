#!/usr/bin/env python
"""
Handles the input of a single url and outputs this to a pipe. Each
chunk of data from the pipe is then routed to the internal pubsub
module to listeners.

The inputStream object is responsible for:

1. automatic restarts of the stream if no output is received after
a configurable amount of time (default 180 seconds).
2. gathers bit rate stats
3. Probes input with ffprobe if this is first time the url
   is used and if there have been more than 3 failed restarts,
   ffprobe's output will be added to a bad stream report.


Configuration spec:

{
    url: "...",
    maxInActvity: 180, # 180 seconds with output and the stream input has failed
    retryAfter: 1800,  # 1800 seconds before stream is restarted
    streamId: "..."
}


"""
import subprocess
import os
import config
import threading
import shlex
import select
import logging
import traceback
import sys
import time
import signals
import readline
from nonblockingReadline import nonblockingReadline

# input stream formats
_isfmt_http = "%s -re -reconnect_at_eof 1 -reconnect_streamed 1 " +\
         "-reconnect_delay_max 2 -i %s -psnr -vstats -f avi pipe:%d"
_isfmt = "%s -re -i %s -psnr -vstats -f avi pipe:%d"
_isfmt_testsrc = "%s -re  -f lavfi -i testsrc=size=352x240:rate=15 -psnr -vstats -f avi pipe:%d"





class InputStream(threading.Thread):
    def __init__(self, conf):
        threading.Thread.__init__(self)
        self.daemon = True 

        self.conf = conf
        self.vout_r, self.vout_w = os.pipe()
        self.cmd_r, self.cmd_w = os.pipe()
        self.proc = None
        self.iomap = {}
        self.sid = conf['streamId']
        self.si_topic = config.StreamInputTopic(self.sid)
        self.ss_topic = config.StreamInputStatsTopic(self.sid)
        self.sf_topic = config.StreamFaultTopic(self.sid)
        self.last_output_time = None
        self.state = config.STREAM_STATE_IDLE

    def __del__(self):
        try:
            os.close(self.vout_r)
            os.close(self.vout_w)
            os.close(self.cmd_r)
            os.close(self.cmd_w)
        except BaseException:
            pass

        if self.proc and not self.proc.poll():
            self.proc.kill()
            self.proc.communicate(b'')

    def _line_proc(self, line):
        logging.debug("line = %s" % line)
        # process stats
        # We're looking for this:
        #  'frame=  138 fps= 11 q=31.0 PSNR=Y:30.88 U:36.31 V:37.12 *:32.10 size=     882kB'
        t = line.split()
        if len(t) > 0 and t[0] == 'frame=':
            def translate(text):
                text = text.replace('kB', ' * 1000')
                text = text.replace('kbits/s', ' * 1000')
                text = text.replace('M', ' * 1000000')
                return eval(text)

            def psnr(t):
                 for tt in t:
                     if tt.startswith('*:'):
                         return float(tt[2:])
                 return 0

            def bitrate(line):
                 pos = line.find('bitrate=')
                 if pos > -1:
                     pos += len('bitrate=')
                     return line[pos:].split()[0]

                 pos = line.find('size=')
                 if pos > -1:
                     return line[pos:].split()[1]
  
                 return "0"              


            logging.debug(psnr)
            input_stats = {
                'fps': t[3],
                # signal to noise ratio, in example: *:(32.10)
                'psnr': psnr(t),
                'bitrate': translate( bitrate(line) )
            }
            logging.debug("received stats: %s" % str(input_stats))
            # route stats to whoever is listening
            signals.publish(self.ss_topic, input_stats)

    def _route_video(self, video_chunk):
        logging.debug(
            "_route_video: %d bytes of video received" %
            len(video_chunk))
        signals.publish(self.si_topic, video_chunk)
        self.state = config.STREAM_STATE_PLAYING
        self.last_output_time = time.time()

    def _inactivity_fault(self):
        """ Test to see if traffic was received from the output pipe conf.maxInActvity
            seconds ago.
        """
        if time.time() > (self.last_output_time + self.conf['maxInActvity']):
            self.state = config.STREAM_STATE_FAULT
            signals.publish(self.sf_topic, {
                'error': 'BadInput',
                'desc': 'No input received after %d seconds' % self.conf['maxInActvity']
            })
            return True
        return False

    def _while_ffmpeg_running(self):
        """
        launch ffmpeg
             route output traffic to stream input topic
             parse
        """
        if self.conf['url'] == 'testsrc':
            cmdargs = (config.FFMPEG, self.vout_w)
            cmd = _isfmt_testsrc % cmdargs
        elif self.conf['url'].startswith('http:'):
            cmdargs = (config.FFMPEG, self.conf['url'], self.vout_w)
            cmd = _isfmt_http % cmdargs            
        else: 
            cmdargs = (config.FFMPEG, self.conf['url'], self.vout_w)
            cmd = _isfmt % cmdargs
        logging.debug(cmd)
        self.proc = subprocess.Popen(
            shlex.split(cmd),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        plist = select.poll()
        plist.register(self.cmd_r, select.POLLIN)
        plist.register(self.vout_r, select.POLLIN)
        plist.register(self.proc.stdout.fileno(), select.POLLIN)
        plist.register(self.proc.stderr.fileno(), select.POLLIN)

        # initialize reference time to now
        self.last_output_time = time.time()

        self.state = config.STREAM_STATE_STARTING
        nb_stdout = nonblockingReadline(self.proc.stdout)
        nb_stderr = nonblockingReadline(self.proc.stderr)
 

        # while ffmpeg is running, theer has been output activity within a configurable
        # amount of time and stream state is not fault.
        while not self.proc.poll() and not self._inactivity_fault() and self.state in (
                config.STREAM_STATE_STARTING, config.STREAM_STATE_PLAYING):

            logging.debug("get next io activity")
            line, video_chunk = None, None
            for (fd, evt) in plist.poll(2000):  # select on 3 sources
                if not (evt & select.POLLIN):
                    self.state = config.STREAM_STATE_FAULT
                    signals.publish(self.sf_topic, {
                        'error': 'SystemError',
                        'desc': 'Pipe I/O error'
                    })
                    break

                if fd == self.cmd_r:
                    self.state = config.STREAM_STATE_STOPPED
                    break

                elif fd == self.proc.stdout.fileno():
                    logging.debug("stdout line")
                    line = nb_stdout.readline()
                elif fd == self.proc.stderr.fileno():
                    logging.debug("stdout error")
                    line = nb_stderr.readline()
                else:
                    video_chunk = os.read(self.vout_r, 0xFFFF)

                if line:
                    self._line_proc(line)
                if video_chunk:
                    self._route_video(video_chunk)
           

        # shutdown ffmpeg and what for process to die so we
        # don't leave defunct process.
        logging.warning("existing ffmpeg loop state=%" % self.state)  
        self.proc.kill()
        self.proc.communicate(b'')
        self.proc = None

    def _while_fault_state(self):
        retry_time = time.time() + self.conf['retryAfter']
        plist = select.poll()
        plist.register(self.cmd_r, select.POLLIN)
        while time.time() < retry_time:
            if len(plist.poll(2000)) > 0:
                self.state = config.STREAM_STATE_STOPPED
                return
        # return to idel state so we can try ffmpeg again
        self.state = config.STREAM_STATE_IDLE

    def _run(self):
        while True:
            if self.state == config.STREAM_STATE_STOPPED:
                # user stopped stream, terminate thread,
                return

            elif self.state == config.STREAM_STATE_IDLE:
                # run ffmpeg route video to stream input topic
                # continue until either state = fault/stopped
                self._while_ffmpeg_running()

            elif self.state == config.STREAM_STATE_FAULT:
                # wait for conf.retryAfter seconds, monitor command pipe
                # since we might receive a stop event while waiting
                self._while_fault_state()

    # start implemented by threading.Thread
    # ...

    def stop(self):
        # any pipe activity
        os.write(self.cmd_w, 'x')

    def run(self):
        # run worker thread that oversees the ffmpeg process, prmorning the
        # task of restarting the stream if need and be and routing video
        # traffic.
        try:
            self._run()
        except BaseException:
            logging.error(traceback.format_exc())
            signals.publish(self.sf_topic, {
                'error': 'SystemError',
                'desc': 'Exception thrown check error log'
            })

        if self.proc and not self.proc.poll():
            self.proc.kill()
            self.proc.communicate(b'')


def unittest():
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG,
        format="%(asctime)s %(message)s")

    sid = "unittest"
    si_topic = config.StreamInputTopic(sid)
    ss_topic = config.StreamInputStatsTopic(sid)
    sf_topic = config.StreamFaultTopic(sid)

    def logmsg(topic):
        def h(*args):
            logging.info("%s, %s" % (topic, str(args)))
        return h

    #signals.subscribe(si_topic, logmsg(si_topic))
    signals.subscribe(ss_topic, logmsg(ss_topic))
    signals.subscribe(sf_topic, logmsg(sf_topic))

    inputStream = InputStream({
    #    "url": "testsrc",
        "url": "rtsp://root:robot@172.28.137.128/axis-media/media.amp", 
        "maxInActvity": 200,
        "retryAfter": 500,
        "streamId": sid
    })
    #inputStream.start()

    inputStream.run()
    time.sleep(30)

    inputStream.stop()


if __name__ == '__main__':
    unittest()

