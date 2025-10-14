# Schrittweiser Implementierungsplan - RA Autohaus Tracker

## Phase 1: Quick Wins (Sofort - 30 Minuten)

### ✅ Task 1.1: Entferne ungenutzte Handler-Variablen
**Datei:** `src/api/routes/integration.py`
```python
# LÖSCHE Zeilen 21-23:
_unified_handler = None  # ← Entfernen
_zapier_handler = None   # ← Entfernen  
_flowers_handler = None  # ← Entfernen
```

### ✅ Task 1.2: Behebe Variable Shadowing
**Datei:** `src/api/routes/vehicles.py` (Zeile 439)
```python
# ALT:
status = vehicle.status or 'Unbekannt'
stats['by_status'][status] = ...

# NEU:
vehicle_status = vehicle.status or 'Unbekannt'
stats['by_status'][vehicle_status] = ...
```

### ✅ Task 1.3: Konsistente Imports
**Alle Route-Dateien:** Ersetze `logging` durch `structlog`
```python
# ALT:
import logging
logger = logging.getLogger(__name__)

# NEU:
import structlog
logger = structlog.get_logger(__name__)
```

**Betroffene Dateien:**
- `src/api/routes/dashboard.py`
- `src/api/routes/email.py`
- `src/api/routes/info.py`
- `src/api/routes/integration.py`
- `src/api/routes/process.py`

---

## Phase 2: Mock-Daten Zentralisierung (1 Stunde)

### ✅ Task 2.1: Erstelle Mock-Data Provider
**Neue Datei:** `src/core/mock_data.py`
```bash
touch src/core/mock_data.py
# Kopiere Code aus Refactoring-Template #1
```

### ✅ Task 2.2: Refactore Dashboard-Service
**Datei:** `src/services/dashboard_service.py`
```python
# Importiere am Anfang:
from src.core.mock_data import MockDataProvider

# Ersetze alle _get_mock_* Methoden durch:
def _get_mock_kpis(self):
    return MockDataProvider.get_dashboard_kpis()
```

### ✅ Task 2.3: Refactore Dashboard-Route
**Datei:** `src/api/routes/dashboard.py`
```python
# Entferne Mock-Daten aus get_prozess_statistik()
# Verwende stattdessen:
from src.core.mock_data import MockDataProvider

statistik = MockDataProvider.get_prozess_statistik(prozess_typ)
```

---

## Phase 3: Validierungs-Refactoring (2 Stunden)

### ✅ Task 3.1: Erstelle Basis-Models
**Datei:** `src/models/base.py` (NEU)
```bash
touch src/models/base.py
# Kopiere Code aus Refactoring-Template #2
```

### ✅ Task 3.2: Refactore Integration Models
**Datei:** `src/models/integration.py`
```python
# Importiere Basis-Klassen:
from src.models.base import BaseProzessModel, BaseTimestampValidation

# Ändere Klassen-Definition:
class FahrzeugProzessCreate(BaseProzessModel, BaseTimestampValidation):
    # ENTFERNE die duplizierten Validatoren
    # Behalte nur die spezifischen Felder
```

### ✅ Task 3.3: Teste Validierung
```bash
# Führe Tests aus
python -m pytest tests/test_models.py -v
```

---

## Phase 4: Error-Handler Implementation (1 Stunde)

### ✅ Task 4.1: Erstelle Error-Handler
**Neue Datei:** `src/core/error_handler.py`
```bash
touch src/core/error_handler.py
# Kopiere Code aus Refactoring-Template #3
```

### ✅ Task 4.2: Refactore Vehicle-Routes
**Datei:** `src/api/routes/vehicles.py`
```python
from src.core.error_handler import APIErrorHandler

# Beispiel-Refactoring für get_vehicle_details():
@router.get("/{fin}")
async def get_vehicle_details(fin: str, ...):
    try:
        fahrzeug = await vehicle_service.get_vehicle_details(fin)
        if not fahrzeug:
            APIErrorHandler.handle_not_found("Fahrzeug", fin)
        return fahrzeug
    except ValueError as e:
        APIErrorHandler.handle_validation_error(e, "Fahrzeugabruf")
    except Exception as e:
        APIErrorHandler.handle_service_error(e, "Fahrzeugabruf")
```

---

## Phase 5: Performance-Optimierung (3 Stunden)

### ✅ Task 5.1: Optimiere Statistik-Berechnung
**Neue Datei:** `src/services/statistics_service.py`
```bash
touch src/services/statistics_service.py
# Kopiere Code aus Refactoring-Template #4
```

### ✅ Task 5.2: Integriere in Vehicle-Route
**Datei:** `src/api/routes/vehicles.py`
```python
from src.services.statistics_service import OptimizedStatisticsService

@router.get("/statistics/summary")
async def get_vehicle_statistics(...):
    stats_service = OptimizedStatisticsService(bigquery_service)
    return await stats_service.get_vehicle_statistics_optimized()
```

### ✅ Task 5.3: Kombiniere Dashboard-Queries
**Datei:** `src/services/bigquery_service.py`
```python
async def get_all_dashboard_data(self) -> Dict[str, Any]:
    """Eine Query für alle Dashboard-Daten"""
    query = """
    WITH all_stats AS (
        -- Kombiniere alle bisherigen Queries
    )
    SELECT * FROM all_stats
    """
    return await self.execute_query(query)
```

---

## Phase 6: Caching-Layer (2 Stunden)

### ✅ Task 6.1: Implementiere Cache-Decorator
**Datei:** `src/core/cache.py` (NEU)
```bash
touch src/core/cache.py
# Kopiere Code aus Refactoring-Template #5
```

### ✅ Task 6.2: Wende Caching auf Dashboard an
**Datei:** `src/services/dashboard_service.py`
```python
from src.core.cache import timed_cache

class DashboardService:
    @timed_cache(seconds=300)  # 5 Minuten Cache
    async def get_kpis(self) -> Dict[str, Any]:
        # Bestehender Code
```

---

## Testing-Checkliste nach jeder Phase

### Unit-Tests
```bash
# Nach Phase 1
python -m pytest tests/test_routes.py::test_integration -v

# Nach Phase 2  
python -m pytest tests/test_mock_data.py -v

# Nach Phase 3
python -m pytest tests/test_models.py::test_validation -v

# Nach Phase 4
python -m pytest tests/test_error_handling.py -v

# Nach Phase 5
python -m pytest tests/test_performance.py -v

# Nach Phase 6
python -m pytest tests/test_caching.py -v
```

### Integration-Tests
```bash
# Lokaler Test
./scripts/start_dev.sh

# API-Test
curl http://localhost:8080/api/v1/fahrzeuge/statistics/summary
curl http://localhost:8080/api/v1/dashboard/kpis

# Performance-Vergleich
time curl http://localhost:8080/api/v1/dashboard/kpis  # Vorher
time curl http://localhost:8080/api/v1/dashboard/kpis  # Nachher (sollte ~50% schneller sein)
```

---

## Git-Workflow

### Für jede Phase:
```bash
# 1. Neuer Branch
git checkout -b refactor/phase-X-beschreibung

# 2. Änderungen committen
git add -p  # Selective staging
git commit -m "refactor(phase-X): Beschreibung der Änderung"

# 3. Push & PR
git push origin refactor/phase-X-beschreibung
# Erstelle Pull Request für Review

# 4. Nach Review mergen
git checkout new-claude
git merge refactor/phase-X-beschreibung
```

---

## Erfolgs-Metriken

### Nach Abschluss aller Phasen sollten folgende Verbesserungen messbar sein:

| Metrik | Vorher | Nachher | Verbesserung |
|--------|--------|---------|--------------|
| Lines of Code | ~2500 | ~2200 | -12% |
| Duplizierter Code | ~15% | <5% | -67% |
| Dashboard Load Time | ~800ms | ~400ms | -50% |
| Memory Usage | ~120MB | ~90MB | -25% |
| Test Coverage | ~60% | >80% | +33% |
| Cyclomatic Complexity | 15-20 | <10 | -40% |

---

## Zeitplan

**Geschätzter Gesamtaufwand:** 10-12 Stunden

### Empfohlene Aufteilung:
- **Tag 1:** Phase 1 + 2 (1,5 Stunden)
- **Tag 2:** Phase 3 (2 Stunden)
- **Tag 3:** Phase 4 (1 Stunde)
- **Tag 4:** Phase 5 (3 Stunden)
- **Tag 5:** Phase 6 + Testing (3 Stunden)

---

## Support & Fragen

Bei Fragen zu einzelnen Phasen:
1. Committe deinen aktuellen Stand
2. Zeige mir die problematische Stelle
3. Ich helfe bei der Lösung

**Viel Erfolg bei der Implementierung! 🚀**