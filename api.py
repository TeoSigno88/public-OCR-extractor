#!/usr/bin/env python3
"""
API REST per OCR Extractor

Espone endpoint REST per l'estrazione di dati da documenti italiani.
Supporta upload di file e invio di Base64.

Endpoints:
- POST /api/carta-identita - Estrae dati da Carta d'Identità
- POST /api/codice-fiscale - Estrae dati da Codice Fiscale
- POST /api/passaporto - Estrae dati da Passaporto
- POST /api/validate-cf - Valida un codice fiscale
- GET /api/health - Health check
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import JSONResponse
import logging
from pydantic import BaseModel
from typing import Optional, Dict, Any
import tempfile
import os
import base64

from ocr_extractor import (
    CartaIdentitaExtractor,
    CodiceFiscaleExtractor,
    PassaportoExtractor
)

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crea l'app FastAPI
app = FastAPI(
    title="OCR Extractor API",
    description="API per l'estrazione di dati da documenti italiani tramite OCR",
    version="1.0.0"
)


# Modelli Pydantic per le richieste
class Base64Request(BaseModel):
    """Richiesta con immagine in Base64"""
    base64: str

    class Config:
        schema_extra = {
            "example": {
                "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            }
        }


class CodiceFiscaleValidateRequest(BaseModel):
    """Richiesta per validazione codice fiscale"""
    codice_fiscale: str

    class Config:
        schema_extra = {
            "example": {
                "codice_fiscale": "RSSMRA85T10A562S"
            }
        }


# Inizializza gli estrattori
carta_extractor = CartaIdentitaExtractor()
cf_extractor = CodiceFiscaleExtractor()
passaporto_extractor = PassaportoExtractor()


@app.get("/")
async def root():
    """Root endpoint con informazioni API"""
    return {
        "name": "OCR Extractor API",
        "version": "1.0.0",
        "endpoints": {
            "carta_identita": "/api/carta-identita",
            "codice_fiscale": "/api/codice-fiscale",
            "passaporto": "/api/passaporto",
            "validate_cf": "/api/validate-cf",
            "health": "/api/health"
        },
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ocr-extractor",
        "version": "1.0.0"
    }


@app.post("/api/carta-identita")
async def extract_carta_identita(file: Optional[UploadFile] = File(None), data: Optional[Base64Request] = Body(None)):
    """
    Estrae dati da una Carta d'Identità

    Supporta:
    - Upload file (multipart/form-data)
    - Base64 (application/json)
    """
    try:
        logger.info(f"Richiesta carta-identita - file: {file is not None}, data: {data is not None}")

        if file:
            # Caso 1: File upload
            logger.info(f"Processando file upload: {file.filename}")
            result = await process_file_upload(file, carta_extractor)
        elif data:
            # Caso 2: Base64
            logger.info(f"Processando Base64 (lunghezza: {len(data.base64)} caratteri)")
            result = carta_extractor.extract_data({'base64': data.base64})
        else:
            logger.warning("Nessun file o dato Base64 fornito")
            raise HTTPException(status_code=400, detail="Fornire un file o dati Base64")

        return JSONResponse(content={
            "success": True,
            "document_type": "carta_identita",
            "data": result
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "document_type": "carta_identita"
            }
        )


@app.post("/api/codice-fiscale")
async def extract_codice_fiscale(file: Optional[UploadFile] = File(None), data: Optional[Base64Request] = Body(None)):
    """
    Estrae e valida un Codice Fiscale

    Supporta:
    - Upload file (multipart/form-data)
    - Base64 (application/json)
    """
    try:
        logger.info(f"Richiesta codice-fiscale - file: {file is not None}, data: {data is not None}")

        if file:
            logger.info(f"Processando file upload: {file.filename}")
            result = await process_file_upload(file, cf_extractor)
        elif data:
            logger.info(f"Processando Base64 (lunghezza: {len(data.base64)} caratteri)")
            result = cf_extractor.extract_data({'base64': data.base64})
        else:
            logger.warning("Nessun file o dato Base64 fornito")
            raise HTTPException(status_code=400, detail="Fornire un file o dati Base64")

        return JSONResponse(content={
            "success": True,
            "document_type": "codice_fiscale",
            "data": result
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "document_type": "codice_fiscale"
            }
        )


@app.post("/api/passaporto")
async def extract_passaporto(file: Optional[UploadFile] = File(None), data: Optional[Base64Request] = Body(None)):
    """
    Estrae dati da un Passaporto

    Supporta:
    - Upload file (multipart/form-data)
    - Base64 (application/json)
    - Estrazione MRZ automatica
    """
    try:
        logger.info(f"Richiesta passaporto - file: {file is not None}, data: {data is not None}")

        if file:
            logger.info(f"Processando file upload: {file.filename}")
            result = await process_file_upload(file, passaporto_extractor)
        elif data:
            logger.info(f"Processando Base64 (lunghezza: {len(data.base64)} caratteri)")
            result = passaporto_extractor.extract_data({'base64': data.base64})
        else:
            logger.warning("Nessun file o dato Base64 fornito")
            raise HTTPException(status_code=400, detail="Fornire un file o dati Base64")

        return JSONResponse(content={
            "success": True,
            "document_type": "passaporto",
            "data": result
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "document_type": "passaporto"
            }
        )


@app.post("/api/validate-cf")
async def validate_codice_fiscale(request: CodiceFiscaleValidateRequest):
    """
    Valida e decodifica un Codice Fiscale senza OCR

    Endpoint utile per validare un codice fiscale già estratto
    """
    try:
        is_valid = cf_extractor.validate_external_codice(request.codice_fiscale)

        if is_valid:
            info = cf_extractor.decode_external_codice(request.codice_fiscale)
            return JSONResponse(content={
                "success": True,
                "valid": True,
                "data": info
            })
        else:
            return JSONResponse(content={
                "success": True,
                "valid": False,
                "message": "Codice fiscale non valido"
            })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@app.post("/api/debug-ocr")
async def debug_ocr(file: UploadFile = File(...)):
    """
    Debug: mostra il testo grezzo estratto da Tesseract senza parsing

    Utile per:
    - Verificare cosa vede Tesseract
    - Diagnosticare problemi di qualità immagine
    - Testare diverse immagini
    """
    import pytesseract
    from PIL import Image

    # Salva file temporaneo
    suffix = os.path.splitext(file.filename)[1] if file.filename else '.tmp'
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = temp_file.name

    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()

        # OCR grezzo con italiano
        img = Image.open(temp_path)

        # Info immagine
        img_info = {
            "format": img.format,
            "mode": img.mode,
            "size": img.size,
            "width": img.width,
            "height": img.height
        }

        # OCR
        text = pytesseract.image_to_string(img, lang='ita')

        # Statistiche
        lines = [line for line in text.split('\n') if line.strip()]

        return JSONResponse(content={
            "success": True,
            "image_info": img_info,
            "raw_text": text,
            "char_count": len(text),
            "word_count": len(text.split()),
            "line_count": len(lines),
            "lines": lines,
            "advice": get_quality_advice(img, text)
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass


def get_quality_advice(img, text: str) -> list:
    """Fornisce consigli sulla qualità dell'immagine"""
    advice = []

    # Verifica risoluzione
    if img.width < 1000 or img.height < 700:
        advice.append("⚠️ Risoluzione bassa. Consigliata: 1500x1000+ pixel")

    # Verifica testo estratto
    if len(text.strip()) < 50:
        advice.append("⚠️ Poco testo estratto. Possibili cause: immagine sfocata, bassa qualità, scarsa illuminazione")

    # Verifica parole riconoscibili
    words = text.split()
    if len(words) < 10:
        advice.append("⚠️ Poche parole riconosciute. Prova con un'immagine più nitida")

    # Consigli generali
    if not advice:
        advice.append("✅ Immagine sembra di buona qualità")
    else:
        advice.append("💡 Usa scansione 300 DPI o foto ben illuminata e a fuoco")

    return advice


async def process_file_upload(file: UploadFile, extractor) -> Dict[str, Any]:
    """
    Helper per processare file upload

    Args:
        file: File caricato
        extractor: Estrattore da utilizzare

    Returns:
        Dati estratti
    """
    # Salva il file temporaneamente
    suffix = os.path.splitext(file.filename)[1] if file.filename else '.tmp'
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = temp_file.name

    try:
        # Scrivi il contenuto del file
        content = await file.read()
        temp_file.write(content)
        temp_file.close()

        # Estrai i dati
        result = extractor.extract_data(temp_path)

        return result

    finally:
        # Pulisci il file temporaneo
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("OCR Extractor API Server")
    print("=" * 60)
    print("\nServer in ascolto su: http://localhost:8000")
    print("Documentazione API: http://localhost:8000/docs")
    print("Alternative docs: http://localhost:8000/redoc")
    print("\nPer testare con Postman:")
    print("  - Importa la collection dalla documentazione OpenAPI")
    print("  - Oppure usa gli endpoint manualmente")
    print("\nPremi CTRL+C per fermare il server")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
