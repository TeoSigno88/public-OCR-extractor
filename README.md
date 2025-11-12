# OCR Extractor - Documenti Italiani

Sistema OCR per l'estrazione automatica di dati da documenti italiani (Carta d'Identità, Codice Fiscale, Passaporto).

## Caratteristiche

- **Supporto Base64**: Accetta immagini in formato Base64 (ideale per PDF convertiti)
- **Supporto File**: Upload diretto di immagini (JPG, PNG, etc.)
- **Pre-processing avanzato**: Miglioramento automatico della qualità per OCR ottimale
- **API REST**: Endpoint pronti per l'integrazione
- **Lingua Italiana**: Ottimizzato per documenti italiani

## Documenti Supportati

✅ **Carta d'Identità** (elettronica e cartacea)
- Nome, Cognome
- Data e luogo di nascita
- Sesso, Statura
- Cittadinanza
- Numero carta
- Date di rilascio/scadenza
- Codice Fiscale

✅ **Codice Fiscale**
- Estrazione automatica
- Validazione checksum
- Decodifica (sesso, data nascita, comune)

✅ **Passaporto**
- Parsing MRZ (Machine Readable Zone)
- Tutti i dati anagrafici
- Numero passaporto
- Date validità

## Prerequisiti

### 1. Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-ita
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
Scarica l'installer da: https://github.com/UB-Mannheim/tesseract/wiki

### 2. Python 3.8+

Verifica la versione:
```bash
python3 --version
```

## Installazione

### 1. Clone o scarica il repository

```bash
git clone https://github.com/your-repo/public-OCR-extractor.git
cd public-OCR-extractor
```

### 2. Crea virtual environment (raccomandato)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows
```

### 3. Installa dipendenze

```bash
pip install -r requirements.txt
```

### 4. Verifica installazione

```bash
python ocr_extractor.py
```

Dovresti vedere:
```
OCR Extractor - Test
============================================================

✓ Estrattori inizializzati correttamente
  - CartaIdentitaExtractor
  - CodiceFiscaleExtractor
  - PassaportoExtractor
...
```

## Avvio del Server API

```bash
python api.py
```

Il server sarà disponibile su: **http://localhost:8000**

Documentazione interattiva: **http://localhost:8000/docs**

## Utilizzo API

### 1. Health Check

```bash
curl http://localhost:8000/api/health
```

### 2. Carta d'Identità - Upload File

```bash
curl -X POST http://localhost:8000/api/carta-identita \
  -F "file=@/path/to/carta-identita.jpg"
```

### 3. Carta d'Identità - Base64

```bash
curl -X POST http://localhost:8000/api/carta-identita \
  -H "Content-Type: application/json" \
  -d '{
    "base64": "iVBORw0KGgoAAAANS..."
  }'
```

**Esempio con file convertito:**

```python
import base64
import requests

# Converti immagine in Base64
with open("carta-identita.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode('utf-8')

# Invia richiesta
response = requests.post(
    "http://localhost:8000/api/carta-identita",
    json={"base64": img_base64}
)

print(response.json())
```

**Risposta:**
```json
{
  "success": true,
  "document_type": "carta_identita",
  "data": {
    "nome": "MARIO",
    "cognome": "ROSSI",
    "data_nascita": "01/01/1985",
    "luogo_nascita": "ROMA",
    "sesso": "M",
    "statura": "175 cm",
    "cittadinanza": "ITALIANA",
    "numero_carta": "CA12345AB",
    "codice_fiscale": "RSSMRA85A01H501X",
    "data_rilascio": "01/01/2020",
    "data_scadenza": "01/01/2030"
  }
}
```

### 4. Codice Fiscale

```bash
curl -X POST http://localhost:8000/api/codice-fiscale \
  -H "Content-Type: application/json" \
  -d '{
    "base64": "iVBORw0KGgoAAAANS..."
  }'
```

### 5. Validazione Codice Fiscale

```bash
curl -X POST http://localhost:8000/api/validate-cf \
  -H "Content-Type: application/json" \
  -d '{
    "codice_fiscale": "RSSMRA85T10A562S"
  }'
```

### 6. Passaporto

```bash
curl -X POST http://localhost:8000/api/passaporto \
  -H "Content-Type: application/json" \
  -d '{
    "base64": "iVBORw0KGgoAAAANS..."
  }'
```

### 7. Debug OCR (solo file upload)

Per vedere il testo grezzo estratto da Tesseract:

```bash
curl -X POST http://localhost:8000/api/debug-ocr \
  -F "file=@/path/to/documento.jpg"
```

## Conversione PDF → Base64

Se hai PDF invece di immagini:

```python
from pdf2image import convert_from_path
import base64
import io

# Converti PDF in immagine (prima pagina)
images = convert_from_path("documento.pdf", first_page=1, last_page=1)
img = images[0]

# Converti in Base64
buffer = io.BytesIO()
img.save(buffer, format='PNG')
img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

# Usa con API
import requests
response = requests.post(
    "http://localhost:8000/api/carta-identita",
    json={"base64": img_base64}
)
```

## Uso Diretto Python (senza API)

```python
from ocr_extractor import CartaIdentitaExtractor, CodiceFiscaleExtractor

# Carta d'Identità da file
carta_ext = CartaIdentitaExtractor()
result = carta_ext.extract_data("/path/to/carta.jpg")
print(result)

# Carta d'Identità da Base64
result = carta_ext.extract_data({"base64": "iVBORw0KG..."})
print(result)

# Codice Fiscale
cf_ext = CodiceFiscaleExtractor()

# Valida CF
is_valid = cf_ext.validate_external_codice("RSSMRA85T10A562S")
print(f"Valido: {is_valid}")

# Decodifica CF
decoded = cf_ext.decode_external_codice("RSSMRA85T10A562S")
print(decoded)
```

## Best Practices per Immagini

Per risultati ottimali:

1. **Risoluzione minima**: 1500x1000 pixel
2. **Formato**: JPG, PNG
3. **Qualità**: Alta risoluzione, ben illuminata
4. **Scansione**: 300 DPI o superiore
5. **Allineamento**: Documento dritto e completo
6. **Focus**: Immagine nitida e a fuoco
7. **Contrasto**: Buon contrasto testo/sfondo

## Troubleshooting

### "Tesseract not found"

Assicurati che Tesseract sia installato e nel PATH:

```bash
tesseract --version
```

Se non funziona, specifica il path manualmente in `ocr_extractor.py`:

```python
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Linux
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows
```

### "Impossibile estrarre dati" / Valori NULL

- Verifica qualità immagine (usa `/api/debug-ocr`)
- Aumenta risoluzione immagine
- Migliora illuminazione/contrasto
- Assicurati che il documento sia completo e leggibile

### Errori con PDF

Installa poppler:

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

## Struttura Progetto

```
public-OCR-extractor/
├── api.py                 # Server API FastAPI
├── ocr_extractor.py       # Motore OCR ed estrattori
├── requirements.txt       # Dipendenze Python
├── README.md             # Questa documentazione
└── TODO.txt              # Note di sviluppo
```

## Endpoints API

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/` | Info API |
| GET | `/api/health` | Health check |
| POST | `/api/carta-identita` | Estrae dati da CI |
| POST | `/api/codice-fiscale` | Estrae CF |
| POST | `/api/passaporto` | Estrae dati passaporto |
| POST | `/api/validate-cf` | Valida CF |
| POST | `/api/debug-ocr` | Debug testo OCR |

## Sviluppo

### Aggiungere nuovo documento

1. Crea nuova classe in `ocr_extractor.py`:

```python
class NuovoDocumentoExtractor(BaseExtractor):
    def _parse_text(self, text: str) -> Dict[str, Any]:
        # Logica parsing
        pass

    def _empty_result(self) -> Dict[str, Any]:
        # Struttura risultato vuoto
        pass
```

2. Aggiungi endpoint in `api.py`

3. Testa con `/api/debug-ocr` per vedere testo grezzo

## Licenza

MIT

## Supporto

Per problemi o domande, apri una issue su GitHub.

## Note

- Il sistema usa Tesseract OCR con lingua italiana
- Le immagini vengono pre-processate automaticamente per migliorare l'OCR
- Il parsing usa regex robuste per gestire variazioni nei documenti
- La validazione del Codice Fiscale include controllo del checksum

## TODO

- [ ] Supporto per altri formati (TIFF, BMP)
- [ ] Riconoscimento automatico tipo documento
- [ ] Batch processing multipli documenti
- [ ] Confidence score per ogni campo estratto
- [ ] Cache risultati
- [ ] Rate limiting
- [ ] Autenticazione API

---

**Versione**: 1.0.0
**Ultimo aggiornamento**: 2024
