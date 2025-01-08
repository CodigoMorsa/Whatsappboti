from pymongo import MongoClient
from config.config import MONGO_URI

# Conectar a MongoDB
client = MongoClient(MONGO_URI)
db = client.whatsapp_boti
recordatorios = db.recordatorios

class Recordatorio:
    def __init__(self, numero, mensaje, fecha):
        self.numero = numero
        self.mensaje = mensaje
        self.fecha = fecha

    def guardar(self):
        db.recordatorios.insert_one(self.__dict__)
