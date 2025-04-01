
from umqtt.simple import MQTTClient
import machine
import esp
import esp32



class MQTT_Handler():
    def __init__(self, client_id, broker, port, user, password):
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.user = user
        self.password = password

