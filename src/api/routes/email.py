"""
Email Routes - Email-Processing Endpoints
Reinhardt Automobile GmbH - RA Autohaus Tracker
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from typing import Dict, Any, cast
import os
import email  # <- Hinzufügen
import imaplib  # <- Hinzufügen
import structlog

from src.services.email_service import EmailService
from src.services.vehicle_service import VehicleService
from src.core.dependencies import get_vehicle_service
from src.models.integration import StandardResponse

router = APIRouter(prefix="/email", tags=["Email"])
logger = structlog.get_logger(__name__)

@router.post(
    "/process",
    response_model=StandardResponse,
    summary="Emails verarbeiten",
    description="Verarbeitet ungelesene Emails und erstellt Fahrzeuge/Prozesse."
)
async def process_emails(
    background_tasks: BackgroundTasks,
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> StandardResponse:
    """
    Startet die Email-Verarbeitung im Hintergrund.
    
    **Funktionsweise:**
    - Liest ungelesene Emails aus dem konfigurierten IMAP-Postfach
    - Parsed Fahrzeugdaten und Prozessinformationen
    - Erstellt/aktualisiert Fahrzeuge in BigQuery
    - Verschiebt verarbeitete Emails in "Verarbeitet" Ordner
    - Fehlerhafte Emails landen im "Fehler" Ordner
    
    **Rückgabe:** Status-Meldung über gestartete Verarbeitung
    """
    try:
        # Email-Konfiguration prüfen
        imap_server = os.getenv('IMAP_SERVER')
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        if not all([imap_server, email_address, email_password]):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email-Konfiguration unvollständig. Bitte Umgebungsvariablen prüfen."
            )
        
        # Email-Service initialisieren
        email_service = EmailService(
        imap_server=cast(str, imap_server),
        email_address=cast(str, email_address),
        password=cast(str, email_password),
        processed_folder=os.getenv('EMAIL_PROCESSED_FOLDER', 'Verarbeitet'),
        error_folder=os.getenv('EMAIL_ERROR_FOLDER', 'Fehler'),
        ignored_folder=os.getenv('EMAIL_IGNORED_FOLDER', 'Ignoriert') 
        )
        
        # Im Hintergrund verarbeiten
        background_tasks.add_task(
            email_service.process_unread_emails,
            vehicle_service
        )
        
        logger.info("📧 Email-Verarbeitung gestartet", 
                   email_address=email_address,
                   imap_server=imap_server)
        
        return StandardResponse(
            success=True,
            message="Email-Verarbeitung wurde gestartet. Die Emails werden im Hintergrund verarbeitet.",
            data={
                "status": "processing",
                "email_account": email_address
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Fehler beim Starten der Email-Verarbeitung", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Starten der Email-Verarbeitung: {str(e)}"
        )

@router.post(
    "/process-sync",
    response_model=Dict[str, Any],
    summary="Emails synchron verarbeiten",
    description="Verarbeitet Emails synchron und gibt direktes Feedback."
)
async def process_emails_sync(
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> Dict[str, Any]:
    """
    Verarbeitet Emails synchron (blockierend).
    
    **Warnung:** Dieser Endpoint blockiert bis alle Emails verarbeitet sind.
    Nutze /process für große Mengen.
    
    **Rückgabe:** Detaillierte Verarbeitungsstatistik
    """
    try:
        # Email-Konfiguration
        imap_server = os.getenv('IMAP_SERVER')
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        if not all([imap_server, email_address, email_password]):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email-Konfiguration unvollständig"
            )
        
        # Email-Service initialisieren
        email_service = EmailService(
        imap_server=cast(str, imap_server),
        email_address=cast(str, email_address),
        password=cast(str, email_password),
        processed_folder=os.getenv('EMAIL_PROCESSED_FOLDER', 'Verarbeitet'),
        error_folder=os.getenv('EMAIL_ERROR_FOLDER', 'Fehler'),
        ignored_folder=os.getenv('EMAIL_IGNORED_FOLDER', 'Ignoriert')
    )  
        # Synchron verarbeiten
        results = await email_service.process_unread_emails(vehicle_service)
        
        logger.info("📧 Email-Verarbeitung abgeschlossen", 
                   processed=results['processed'],
                   created=results['fahrzeuge_created'],
                   updated=results['fahrzeuge_updated'])
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Fehler bei synchroner Email-Verarbeitung", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei Email-Verarbeitung: {str(e)}"
        )

@router.get(
    "/config",
    summary="Email-Konfiguration prüfen",
    description="Zeigt die aktuelle Email-Konfiguration (ohne Passwort)."
)
async def check_email_config() -> Dict[str, Any]:
    """
    Prüft und zeigt die Email-Konfiguration.
    
    **Rückgabe:** Konfigurationsstatus ohne sensitive Daten
    """
    config = {
        'configured': False,
        'imap_server': os.getenv('IMAP_SERVER'),
        'email_address': os.getenv('EMAIL_ADDRESS'),
        'password_set': bool(os.getenv('EMAIL_PASSWORD')),
        'processed_folder': os.getenv('EMAIL_PROCESSED_FOLDER', 'Verarbeitet'),
        'error_folder': os.getenv('EMAIL_ERROR_FOLDER', 'Fehler')
    }

    if all([config['imap_server'], config['email_address'], config['password_set']]):
        config['configured'] = True
    
    return config
    
@router.get(
    "/status",
    summary="Email-Status prüfen",
    description="Zeigt die Anzahl ungelesener Emails und weitere Informationen."
)
async def check_email_status() -> Dict[str, Any]:
    """
    Prüft den Email-Status ohne Emails zu verarbeiten.
    
    **Rückgabe:**
    - unread_count: Anzahl ungelesener Emails
    - folder_info: Ordner-Struktur
    - connection_status: Verbindungsstatus
    """
    import imaplib
    
    try:
        # Email-Konfiguration
        imap_server = os.getenv('IMAP_SERVER')
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        if not all([imap_server, email_address, email_password]):
            return {
                'status': 'unconfigured',
                'message': 'Email-Konfiguration unvollständig'
            }
        
        # IMAP-Verbindung testen
        mail = imaplib.IMAP4_SSL(cast(str, imap_server))
        mail.login(cast(str, email_address), cast(str, email_password))
                
        # INBOX auswählen
        status, messages = mail.select('INBOX')
        if status != 'OK':
            return {
                'status': 'error',
                'message': 'Konnte INBOX nicht öffnen'
            }
        
        # Ungelesene Emails zählen
        status, unread_data = mail.search(None, 'UNSEEN')
        unread_ids = unread_data[0].split() if unread_data[0] else []
        
        # Alle Emails zählen
        status, all_data = mail.search(None, 'ALL')
        all_ids = all_data[0].split() if all_data[0] else []
        
        # Ordner auflisten
        status, folder_list = mail.list()
        folders = []
        if status == 'OK':
            for folder_data in folder_list:
                if isinstance(folder_data, bytes):
                    # Parse folder name from IMAP response
                    parts = folder_data.decode().split('"')
                    if len(parts) >= 3:
                        folders.append(parts[-2])
        
        mail.close()
        mail.logout()
        
        return {
            'status': 'connected',
            'connection': {
                'server': imap_server,
                'account': email_address
            },
            'inbox': {
                'total_emails': len(all_ids),
                'unread_emails': len(unread_ids),
                'email_ids': [id.decode() for id in unread_ids[:10]]  # Erste 10 IDs
            },
            'folders': {
                'available': folders,
                'processed': os.getenv('EMAIL_PROCESSED_FOLDER', 'Verarbeitet'),
                'error': os.getenv('EMAIL_ERROR_FOLDER', 'Fehler')
            }
        }
        
    except imaplib.IMAP4.error as e:
        logger.error("❌ IMAP-Fehler", error=str(e))
        return {
            'status': 'error',
            'message': f'IMAP-Fehler: {str(e)}'
        }
    except Exception as e:
        logger.error("❌ Allgemeiner Fehler", error=str(e))
        return {
            'status': 'error',
            'message': str(e)
        }


@router.post(
    "/test",
    summary="Test-Email verarbeiten",
    description="Verarbeitet nur die erste ungelesene Email zum Testen."
)
async def test_process_single_email(
    vehicle_service: VehicleService = Depends(get_vehicle_service)
) -> Dict[str, Any]:
    """
    Verarbeitet nur eine einzelne Email für Testzwecke.
    
    **Rückgabe:** Details zur verarbeiteten Test-Email
    """
    import imaplib
    
    try:
        # Email-Service initialisieren
        imap_server = os.getenv('IMAP_SERVER')
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        if not all([imap_server, email_address, email_password]):
            raise HTTPException(
                status_code=503,
                detail="Email-Konfiguration unvollständig"
            )
        
        email_service = EmailService(
            imap_server=cast(str, imap_server),
            email_address=cast(str, email_address),
            password=cast(str, email_password),
            processed_folder=os.getenv('EMAIL_PROCESSED_FOLDER', 'Verarbeitet'),
            error_folder=os.getenv('EMAIL_ERROR_FOLDER', 'Fehler'),
            ignored_folder=os.getenv('EMAIL_IGNORED_FOLDER', 'Ignoriert')
        )
        
        # Nur erste Email holen
        mail = imaplib.IMAP4_SSL(cast(str, imap_server))
        mail.login(cast(str, email_address), cast(str, email_password))
        mail.select('INBOX')
        
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK' or not messages[0]:
            return {
                'status': 'no_emails',
                'message': 'Keine ungelesenen Emails vorhanden'
            }
        
        email_ids = messages[0].split()
        first_email_id = email_ids[0]
        
        # Email abrufen und parsen
        status, msg_data = mail.fetch(first_email_id, '(RFC822)')
        if status != 'OK' or not msg_data or not msg_data[0]:
            return {'status': 'error', 'message': 'Konnte Email nicht abrufen'}
        
        raw_email = msg_data[0][1]
        if not isinstance(raw_email, bytes):
            return {'status': 'error', 'message': 'Email-Format ungültig'}
        
        msg = email.message_from_bytes(raw_email)
        subject = email_service._decode_header(msg['Subject'])
        body = email_service._extract_body(msg)
        
        # Parsing testen
        fahrzeug_dict, prozess_dict = email_service.parser.parse_email_content(subject, body)
        
        mail.close()
        mail.logout()
        
        return {
            'status': 'parsed',
            'email': {
                'id': first_email_id.decode(),
                'subject': subject,
                'body_preview': body[:500] if body else None
            },
            'parsed_data': {
                'fahrzeug': fahrzeug_dict,
                'prozess': prozess_dict
            },
            'would_create': {
                'fahrzeug': fahrzeug_dict is not None,
                'prozess': prozess_dict is not None
            }
        }
        
    except Exception as e:
        logger.error("❌ Test-Fehler", error=str(e))
        return {
            'status': 'error',
            'message': str(e)
        }

