import os
import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Conectar a MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client.whatsapp_boti
recordatorios = db.recordatorios

# Configurar Flask
app = Flask(__name__)

# 📌 Función para guardar eventos en MongoDB
def guardar_evento(nombre_evento, fecha, usuario):
    evento = {
        "fecha": fecha.strftime("%Y-%m-%d %H:%M:%S"),
        "usuario": usuario,
        "evento": nombre_evento
    }
    recordatorios.insert_one(evento)
    return True

# 📌 Webhook de WhatsApp
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").lower()
    from_number = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg.startswith("evento"):
        try:
            partes = incoming_msg.split(" ")
            nombre = " ".join(partes[1:-1])
            tiempo = int(partes[-1])
            fecha = datetime.datetime.now() + datetime.timedelta(minutes=tiempo)

            if guardar_evento(nombre, fecha, from_number):
                msg.body(f"✅ Evento '{nombre}' guardado en MongoDB.")
            else:
                msg.body("❌ Error al guardar el evento en MongoDB.")
        except:
            msg.body("❌ Usa: Evento <nombre> <minutos>")

    else:
        msg.body("💬 Comandos disponibles:\n1️⃣ Evento <nombre> <minutos>\n")

    return str(resp)

# Ejecutar servidor
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
