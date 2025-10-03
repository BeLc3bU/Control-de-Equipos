# email_utils.py
import webbrowser
import urllib.parse
from logger import logger
from ui_utils import show_info, show_error

def send_email_notification(subject: str, body: str):
    """
    Abre el cliente de correo web (Gmail) con un borrador pre-rellenado.
    El usuario deberá añadir el destinatario manualmente.
    """
    try:
        encoded_subject = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(body)
        
        # El campo 'to' se deja vacío para que el usuario lo rellene.
        url = f"https://mail.google.com/mail/?view=cm&fs=1&su={encoded_subject}&body={encoded_body}"
        
        webbrowser.open(url)
        logger.info(f"Abriendo Gmail para enviar correo con asunto: {subject}")
        show_info("Redactar Correo", "Se ha abierto una ventana en tu navegador para redactar el correo.")
    except Exception as e:
        logger.error(f"Error al intentar abrir el navegador: {e}")
        show_error("Error", f"No se pudo abrir el navegador para redactar el correo.\nError: {e}")