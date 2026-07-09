#!/usr/bin/env python3
"""
Test per API Server

Test degli endpoint API con richieste reali
"""

import subprocess
import time
import requests
import base64
import io
from PIL import Image


def create_test_image_base64():
    """Crea un'immagine di test in Base64"""
    # Crea immagine bianca con testo simulato
    img = Image.new('RGB', (1500, 1000), color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def test_api():
    """Test degli endpoint API"""
    base_url = "http://localhost:8000"

    print("=" * 70)
    print("TEST API SERVER")
    print("=" * 70)
    print()

    # Test 1: Health check
    print("1. Test Health Check")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print("   ✓ Health check OK")
            print(f"   Status: {response.json()['status']}")
        else:
            print(f"   ✗ Health check FAILED: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ✗ Server non raggiungibile. Avvia il server con: python api.py")
        return False
    except Exception as e:
        print(f"   ✗ Errore: {e}")
        return False

    print()

    # Test 2: Root endpoint
    print("2. Test Root Endpoint")
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("   ✓ Root endpoint OK")
            print(f"   API: {data['name']}")
            print(f"   Version: {data['version']}")
        else:
            print(f"   ✗ Root FAILED: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Errore: {e}")

    print()

    # Test 3: POST Carta Identità (senza file, dovrebbe dare errore 400)
    print("3. Test POST Carta Identità senza dati")
    try:
        response = requests.post(
            f"{base_url}/api/carta-identita",
            json={},
            timeout=5
        )
        if response.status_code == 400:
            print("   ✓ Validazione OK (errore 400 atteso)")
        else:
            print(f"   ✗ Status code inaspettato: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Errore: {e}")

    print()

    # Test 4: POST con Base64
    print("4. Test POST Carta Identità con Base64")
    try:
        b64_data = create_test_image_base64()
        response = requests.post(
            f"{base_url}/api/carta-identita",
            json={"base64": b64_data},
            timeout=10
        )

        if response.status_code in [200, 500]:
            data = response.json()
            print(f"   ✓ Richiesta completata (status: {response.status_code})")
            print(f"   Success: {data.get('success', False)}")
            print(f"   Document type: {data.get('document_type', 'N/A')}")

            if not data.get('success'):
                print(f"   Nota: Nessun dato estratto (immagine di test vuota)")
        else:
            print(f"   ✗ Status code inaspettato: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Errore: {e}")

    print()

    # Test 5: Validazione Codice Fiscale
    print("5. Test Validazione Codice Fiscale")
    try:
        response = requests.post(
            f"{base_url}/api/validate-cf",
            json={"codice_fiscale": "RSSMRA85T10A562S"},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            print("   ✓ Validazione completata")
            print(f"   Valido: {data.get('valid', False)}")
            if data.get('valid') and 'data' in data:
                print(f"   Sesso: {data['data'].get('sesso', 'N/A')}")
                print(f"   Anno: {data['data'].get('anno_nascita', 'N/A')}")
        else:
            print(f"   ✗ FAILED: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Errore: {e}")

    print()
    print("=" * 70)
    print("TEST COMPLETATI")
    print("=" * 70)

    return True


if __name__ == "__main__":
    print("\nVerifica che il server sia in esecuzione su http://localhost:8000")
    print("Se non è avviato, esegui: python api.py")
    print()

    input("Premi ENTER per continuare...")
    print()

    test_api()
