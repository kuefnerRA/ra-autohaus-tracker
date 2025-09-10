import imaplib
import os
from dotenv import load_dotenv

load_dotenv()

# Credentials aus .env laden
server = os.getenv('IMAP_SERVER')
email = os.getenv('EMAIL_ADDRESS')
password = os.getenv('EMAIL_PASSWORD')

print(f"Server: {server}")
print(f"Email: {email}")
print(f"Password: {'*' * len(password) if password else 'NOT SET'}")

try:
    # Verbindung aufbauen
    print(f"\nVerbinde zu {server}...")
    mail = imaplib.IMAP4_SSL(server)
    
    # Login versuchen
    print(f"Login als {email}...")
    mail.login(email, password)
    
    print("✓ Login erfolgreich!")
    
    # Inbox auswählen
    status, messages = mail.select('INBOX')
    print(f"✓ INBOX ausgewählt: {status}")
    
    # Anzahl Emails
    status, data = mail.search(None, 'ALL')
    if status == 'OK':
        email_ids = data[0].split()
        print(f"✓ Gefundene Emails: {len(email_ids)}")
    
    # Verbindung schließen
    mail.logout()
    print("✓ Verbindung geschlossen")
    
except imaplib.IMAP4.error as e:
    print(f"✗ IMAP-Fehler: {e}")
except Exception as e:
    print(f"✗ Fehler: {e}")