import json
import os 
import logging

DATA_DIR = "/opt/iffmpeg/"
RAMDISK_DIR = DATA_DIR+"ramdisk" 
ASSETS_DIR = DATA_DIR+"assets"


MQTT_BROKER_IP="localhost"
MQTT_BROKER_PORT=1883
MQTT_SERVICE_DOWN_TOPIC="worldview/node/down"

def StreamInputTopic(streamId): 
    return streamId+"-input-chunk"
def StreamInputStatsTopic(streamId): 
    return streamId+"-input-stats"
def ImageTopic(streamId):
    return streamId+"-image-ready"
def StreamStopTopic(streamId):
    return streamId+"-stop"
def StreamFaultTopic(streamId):
    return streamId+"-fault"

STREAM_CREATE_TOPIC="create"

CurrentPath = os.path.dirname(os.path.realpath(__file__))
FFMPEG = os.popen("which ffmpeg").read()[:-1]
FFPROBE = os.popen("which ffprobe").read()[:-1]

STREAM_STATE_IDLE="idle"
STREAM_STATE_STARTING="starting"
STREAM_STATE_FAULT="fault"
STREAM_STATE_STOPPED="stopped"
STREAM_STATE_PLAYING="playing"



def load(filename):
    if os.access(filename,os.F_OK):
        return json.loads(open(filename).read())
        


