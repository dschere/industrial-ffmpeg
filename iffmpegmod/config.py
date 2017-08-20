import json
import os 
import logging

DATA_DIR = "/opt/iffmpeg/"

CurrentPath = os.path.dirname(os.path.realpath(__file__))
FFMPEG = os.popen("which ffmpeg").read()
FFPROBE = os.popen("which ffprobe").read()

if os.access(CurrentPath+"/basic-config.json",os.F_OK):
    jobj = json.loads(open(CurrentPath+"/basic-config.json").read())
    if jobj.get('ffmpegPath'):
        FFMPEG=jobj.get('ffmpegPath')+"/ffmpeg"          
        FFPROBE=jobj.get('ffmpegPath')+"/ffprobe"    



