import logging
import traceback

__pubsub = {}

def subscribe(topic, callback):
    global __pubsub

    logging.debug("subscribe to %s, callback = %s" % (
        topic, str(callback) ))

    if topic not in __pubsub: 
        __pubsub[topic] = []
    __pubsub[topic].append(callback)

def unsubscribe(topic, callback):
    global __pubsub

    logging.debug("unsubscribe to %s, callback = %s" % (
        topic, str(callback) ))

    if topic not in __pubsub and callback in __pubsub[topic]:
        del __pubsub[topic][ __pubsub[topic].index(callback) ]
        if len(__pubsub[topic]) == 0:
            del __pubsub[topic]

def publish(topic, *args):
    if topic in __pubsub:
        for cb in __pubsub[topic]:
            try:  
                cb( *args )
            except:
                logging.error(traceback.format_exc())
 


