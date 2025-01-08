from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from pymongo import MongoClient
import os
import schedule
import time
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import googleapiclient.discovery
from google.oauth2 import service_account

app = Flask(__name__)

# Conectar a MongoDB
client = MongoClient(os.environ.get("MONGO_URI"))
db = client.whatsapp_boti
eventos = db["eventos"]
enlaces = db["enlaces"]
alarmas = db["alarmas"]

# Configurar Google Calendar API
SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = "service_account.json"

import json
credentials_info = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
credentials = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)


service = googleapiclient.discovery.build("calendar", "v3", credentials=credentials)


# 📅 Función para Guardar un Evento
def guardar_evento(usuario, fecha, hora, titulo, recordatorio_dias, recordatorio_horas):
    """Guarda un evento en la base de datos."""
    eventos.insert_one({
        "usuario": usuario,
        "titulo": titulo,
        "fecha": fecha,
        "hora": hora,
        "recordatorio_dias": recordatorio_dias,
        "recordatorio_horas": recordatorio_horas,
        "telefono": usuario
    })
    return f"✅ Evento '{titulo}' guardado para el {fecha} a las {hora}."


# 🔔 Verificar y Enviar Recordatorios Automáticos
def verificar_recordatorios():
    """Revisa los eventos almacenados y envía recordatorios cuando sea necesario."""
    ahora = datetime.now()
    eventos_pendientes = eventos.find({})

    for evento in eventos_pendientes:
        fecha_evento = datetime.strptime(f"{evento['fecha']} {evento['hora']}", "%Y-%m-%d %H:%M")
        recordatorio = fecha_evento - timedelta(days=evento["recordatorio_dias"], hours=evento["recordatorio_horas"])

        if ahora >= recordatorio:
            enviar_mensaje_whatsapp(evento["telefono"], f"📅 Recordatorio: {evento['titulo']} es el {evento['fecha']} a las {evento['hora']} ⏰")
            eventos.delete_one({"_id": evento["_id"]})


# 🔗 Función para Guardar Enlaces
def guardar_enlace(usuario, titulo, url):
    """Guarda un enlace en MongoDB."""
    enlaces.insert_one({
        "usuario": usuario,
        "titulo": titulo,
        "url": url,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    return "✅ Enlace guardado correctamente."


# 📋 Listar Eventos Guardados
def listar_eventos():
    """Obtiene todos los eventos almacenados en la base de datos y los muestra en formato lista."""
    eventos_guardados = eventos.find({})

    if eventos.count_documents({}) == 0:
        return "📅 No tienes eventos programados."

    respuesta = "📅 Lista de eventos:\n"
    for evento in eventos_guardados:
        respuesta += f"🔹 {evento['titulo']} - 📆 {evento['fecha']} ⏰ {evento['hora']}\n"

    return respuesta


# 📋 Listar Enlaces Guardados
def listar_enlaces():
    """Obtiene todos los enlaces guardados."""
    enlaces_guardados = enlaces.find({})

    if enlaces.count_documents({}) == 0:
        return "🔗 No tienes enlaces guardados."

    respuesta = "🔗 Lista de enlaces guardados:\n"
    for enlace in enlaces_guardados:
        respuesta += f"🔹 {enlace['titulo']} - {enlace['url']}\n"

    return respuesta


# ⏰ Función para Agregar una Alarma en Google Calendar
def agregar_alarma(usuario, fecha, hora, titulo):
    """Añade una alarma a Google Calendar."""
    fecha_hora = f"{fecha}T{hora}:00"
    evento = {
        "summary": titulo,
        "start": {"dateTime": fecha_hora, "timeZone": "UTC"},
        "end": {"dateTime": fecha_hora, "timeZone": "UTC"},
        "reminders": {"useDefault": True},
    }

    service.events().insert(calendarId="primary", body=evento).execute()
    return f"⏰ Alarma programada para '{titulo}' el {fecha} a las {hora}."


# ℹ️ Mostrar Lista de Comandos
def mostrar_comandos():
    """Muestra la lista de comandos disponibles en el bot."""
    return (
        "🤖 *Comandos de Boubert*\n\n"
        "📅 *Eventos y Recordatorios:*\n"
        "🔹 `Lista de eventos` → Muestra todos los eventos guardados.\n"
        "🔹 `Evento [fecha] [hora] [descripción] [recordatorio días] [recordatorio horas]` → Guarda un evento.\n"
        "🔹 `Eliminar evento [nombre]` → Elimina un evento específico.\n\n"
        "📌 *Enlaces Guardados:*\n"
        "🔹 `Guardar enlace [título] [URL]` → Guarda un enlace.\n"
        "🔹 `Lista de enlaces` → Muestra los enlaces guardados.\n\n"
        "⏰ *Alarmas:*\n"
        "🔹 `Pon una alarma [fecha] [hora] [título]` → Configura una alarma.\n\n"
        "ℹ️ *Información:* \n"
        "🔹 `Ayuda` o `Comandos` → Muestra esta lista de comandos.\n"
    )


# 📲 Manejo de Mensajes en WhatsApp
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").lower()
    from_number = request.values.get("From")

    respuesta = "❌ No entendí tu mensaje. Escribe 'comandos' para ver las opciones."

    if "evento" in incoming_msg:
        partes = incoming_msg.split(" ", 6)
        if len(partes) == 6:
            fecha, hora, titulo, recordatorio_dias, recordatorio_horas = partes[1], partes[2], partes[3], int(partes[4]), int(partes[5])
            respuesta = guardar_evento(from_number, fecha, hora, titulo, recordatorio_dias, recordatorio_horas)
    
    elif "lista de eventos" in incoming_msg:
        respuesta = listar_eventos()

    elif "guardar enlace" in incoming_msg:
        partes = incoming_msg.split(" ", 2)
        if len(partes) == 3:
            titulo, url = partes[1], partes[2]
            respuesta = guardar_enlace(from_number, titulo, url)
    
    elif "lista de enlaces" in incoming_msg:
        respuesta = listar_enlaces()

    elif "pon una alarma" in incoming_msg:
        partes = incoming_msg.split(" ", 4)
        if len(partes) == 4:
            fecha, hora, titulo = partes[1], partes[2], partes[3]
            respuesta = agregar_alarma(from_number, fecha, hora, titulo)

    elif incoming_msg in ["ayuda", "comandos"]:
        respuesta = mostrar_comandos()
    
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(respuesta)
    return str(resp)


# 🔄 Iniciar el scheduler para los recordatorios
scheduler = BackgroundScheduler()
scheduler.add_job(verificar_recordatorios, "interval", minutes=1)
scheduler.start()


# 🚀 Iniciar el servidor Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
