#!/usr/bin/env python
"""
Runs the iffmpeg daemon service. 
"""
import config
from pubsub import pub
import paho.mqtt.client as mqtt
import json

class MqttCommunication:
    def __init__(self, streamId):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.will_set(config.MQTT_SERVICE_DOWN_TOPIC, 
            payload=json.dumps({
                "id": serviceId
            })
        )
        self.routes = {}
        self.sid = streamId
        self.client.connect(config.MQTT_BROKER_IP, config.MQTT_BROKER_PORT, 60)

    def mqtt_send(self, topic="",data=""):
        self.client.publish(topic,payload=data)
   
    def mqtt_listen(self, topic="", handler=None):
        self.routes[topic] = handler

    def start(self):
        self.client.start_loop()
        
    def stop(self):
        self.client.stop_loop()

     # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        pub.subscribe(self.mqtt_send,"mqtt-send")
        pub.subscribe(self.mqtt_listen,"mqtt-listen")
        pub.sendMessage("mqtt-ready", streamId=self.sid)

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        cb = self.routes.get(msg.topic)
        if cb:
            cb(msg)
            

