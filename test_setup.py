#!/usr/bin/env python3
"""
Setup-Test für RA Autohaus Tracker
"""

def test_imports():
    """Testet ob alle wichtigen Module importiert werden können."""
    try:
        import fastapi
        print("✅ FastAPI importiert")
        
        import uvicorn
        print("✅ Uvicorn importiert")
        
        import pydantic
        print("✅ Pydantic importiert")
        
        import structlog
        print("✅ Structlog importiert")
        
        print("\n🎉 Alle Basis-Module erfolgreich importiert!")
        return True
        
    except ImportError as e:
        print(f"❌ Import-Fehler: {e}")
        return False

def test_app():
    """Testet ob die FastAPI App startet."""
    try:
        from src.main import app
        print("✅ FastAPI App erfolgreich importiert")
        return True
    except Exception as e:
        print(f"❌ App-Import-Fehler: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Teste Setup...")
    
    if test_imports() and test_app():
        print("\n✅ Setup-Test erfolgreich!")
        print("🚀 Du kannst jetzt mit der Entwicklung beginnen:")
        print("   uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload")
    else:
        print("\n❌ Setup-Test fehlgeschlagen")
        print("   Prüfe die Fehler oben und führe 'pip install -r requirements.txt' erneut aus")
