import signals
import config

"""
Describes at a high level a filter graph composed of processes
working togther to achieve a video stream. Below is an example

         ++---> image generator --> analytics for video outage detection
         ||
Input1 ---+--+
         |    )--- transcode --+---> nginx for distribution
Input2 --+---+                 |
                           recording   

"""




class StreamInputs:
    def __init__(self):
        # mode can be single|videoWall|tour
        self.mode = None 
        # [{
        #     url: ...,
        #     duration: ..., <- if mode=tour
        #     panel: ..,  <- if mode=videoWall    
        # }]
        self.src = [] 

 

class StreamAnalytics:
    def __init__(self):
        self.enabled = False
        self.motion_detector = False 

class Stream:
    def __init__(self, sid):
        self.sid = sid
        self.inputs = StreamInputs()
        self.analytics = StreamAnalytics()
        self.desturl = None
        self.record = False
        # enabled|disabled|outage        
        self.state = None    
            
    def setup(self):
        signals.publish(config.STREAM_CREATE_TOPIC, self) 

