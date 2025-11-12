#!/usr/bin/env python3
"""
OCR Extractor per documenti italiani

Estrae informazioni strutturate da:
- Carta d'Identità (elettronica e cartacea)
- Codice Fiscale
- Passaporto

Supporta immagini e Base64 (da immagini/PDF convertiti)
"""

import re
import base64
import io
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
from PIL import Image
import pytesseract
import cv2
import numpy as np

# Configura logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseExtractor:
    """Classe base per tutti gli estrattori OCR"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_data(self, source: Union[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        Estrae dati dal documento

        Args:
            source: Path del file o dict con chiave 'base64'

        Returns:
            Dizionario con i dati estratti
        """
        try:
            # Carica l'immagine
            img = self._load_image(source)

            if img is None:
                self.logger.error("Impossibile caricare l'immagine")
                return self._empty_result()

            # Pre-processing dell'immagine
            processed_img = self._preprocess_image(img)

            # Estrai testo con OCR
            text = self._extract_text(processed_img)

            if not text or len(text.strip()) < 10:
                self.logger.warning(f"Testo estratto troppo corto: {len(text)} caratteri")
                return self._empty_result()

            self.logger.info(f"Testo estratto: {len(text)} caratteri")
            self.logger.debug(f"Testo grezzo:\n{text}")

            # Parsing specifico per tipo documento
            result = self._parse_text(text)

            return result

        except Exception as e:
            self.logger.exception(f"Errore durante l'estrazione: {e}")
            return self._empty_result()

    def _load_image(self, source: Union[str, Dict[str, str]]) -> Optional[np.ndarray]:
        """Carica immagine da file o Base64"""
        try:
            if isinstance(source, dict) and 'base64' in source:
                # Decodifica Base64
                base64_str = source['base64']

                # Rimuovi prefix se presente (data:image/png;base64,...)
                if ',' in base64_str:
                    base64_str = base64_str.split(',', 1)[1]

                # Decodifica
                img_data = base64.b64decode(base64_str)

                # Converti in immagine PIL
                pil_img = Image.open(io.BytesIO(img_data))

                # Converti in formato OpenCV (numpy array)
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

                self.logger.info(f"Immagine caricata da Base64: {img.shape}")
                return img

            elif isinstance(source, str):
                # Carica da file
                img = cv2.imread(source)

                if img is None:
                    self.logger.error(f"Impossibile leggere il file: {source}")
                    return None

                self.logger.info(f"Immagine caricata da file: {img.shape}")
                return img

            else:
                self.logger.error(f"Formato source non supportato: {type(source)}")
                return None

        except Exception as e:
            self.logger.exception(f"Errore nel caricamento immagine: {e}")
            return None

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        Pre-processing per migliorare l'OCR

        - Conversione in scala di grigi
        - Ridimensionamento se troppo piccola
        - Denoising
        - Binarizzazione adattiva
        - Sharpening
        """
        try:
            # Converti in scala di grigi
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img

            # Ridimensiona se l'immagine è troppo piccola
            height, width = gray.shape
            if width < 1500:
                scale = 1500 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                self.logger.info(f"Immagine ridimensionata a {new_width}x{new_height}")

            # Denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

            # Binarizzazione adattiva
            binary = cv2.adaptiveThreshold(
                denoised,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )

            # Sharpening kernel
            kernel = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]])
            sharpened = cv2.filter2D(binary, -1, kernel)

            return sharpened

        except Exception as e:
            self.logger.warning(f"Errore nel pre-processing, uso immagine originale: {e}")
            return img

    def _extract_text(self, img: np.ndarray) -> str:
        """Estrae testo dall'immagine con Tesseract"""
        try:
            # Configurazione Tesseract per italiano
            custom_config = r'--oem 3 --psm 6 -l ita'

            # Estrai testo
            text = pytesseract.image_to_string(img, config=custom_config)

            return text

        except Exception as e:
            self.logger.exception(f"Errore nell'estrazione testo: {e}")
            return ""

    def _parse_text(self, text: str) -> Dict[str, Any]:
        """Da implementare nelle sottoclassi"""
        raise NotImplementedError

    def _empty_result(self) -> Dict[str, Any]:
        """Da implementare nelle sottoclassi"""
        raise NotImplementedError

    def _clean_text(self, text: str) -> str:
        """Pulisce il testo rimuovendo caratteri indesiderati"""
        if not text:
            return ""
        # Rimuovi caratteri di controllo e spazi multipli
        cleaned = re.sub(r'\s+', ' ', text)
        return cleaned.strip()

    def _extract_date(self, text: str, patterns: list) -> Optional[str]:
        """Estrae data con vari pattern"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1) if match.groups() else match.group(0)
                # Normalizza formato
                date_str = re.sub(r'\s+', ' ', date_str).strip()
                return date_str
        return None


class CartaIdentitaExtractor(BaseExtractor):
    """Estrattore per Carta d'Identità (elettronica e cartacea)"""

    def _parse_text(self, text: str) -> Dict[str, Any]:
        """Parsing specifico per carta d'identità"""

        result = {
            'nome': None,
            'cognome': None,
            'data_nascita': None,
            'luogo_nascita': None,
            'sesso': None,
            'statura': None,
            'cittadinanza': None,
            'comune_rilascio': None,
            'data_rilascio': None,
            'data_scadenza': None,
            'numero_carta': None,
            'codice_fiscale': None,
            'raw_text': text
        }

        lines = text.split('\n')
        text_upper = text.upper()

        # Nome
        nome_match = re.search(r'NOME[:\s]*([A-Z\s]+)', text_upper)
        if nome_match:
            result['nome'] = self._clean_text(nome_match.group(1))

        # Cognome
        cognome_match = re.search(r'COGNOME[:\s]*([A-Z\s]+)', text_upper)
        if cognome_match:
            result['cognome'] = self._clean_text(cognome_match.group(1))

        # Data di nascita
        data_nascita_patterns = [
            r'NATO/A\s+IL[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
            r'DATA\s+DI\s+NASCITA[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
            r'NASC[A-Z]*[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})'
        ]
        result['data_nascita'] = self._extract_date(text_upper, data_nascita_patterns)

        # Luogo di nascita
        luogo_match = re.search(r'NATO/A\s+A[:\s]*([A-Z\s]+?)(?:IL|DATA|NASC|\d|$)', text_upper)
        if not luogo_match:
            luogo_match = re.search(r'LUOGO\s+DI\s+NASCITA[:\s]*([A-Z\s]+?)(?:\n|$)', text_upper)
        if luogo_match:
            result['luogo_nascita'] = self._clean_text(luogo_match.group(1))

        # Sesso
        sesso_match = re.search(r'SESSO[:\s]*([MF])', text_upper)
        if sesso_match:
            result['sesso'] = sesso_match.group(1)

        # Statura
        statura_match = re.search(r'STATURA[:\s]*(\d+)', text_upper)
        if statura_match:
            result['statura'] = statura_match.group(1) + ' cm'

        # Cittadinanza
        cittadinanza_match = re.search(r'CITTADINANZA[:\s]*([A-Z]+)', text_upper)
        if not cittadinanza_match:
            # Spesso è ITALIANA di default
            if 'CITTADINANZA' in text_upper:
                result['cittadinanza'] = 'ITALIANA'
        else:
            result['cittadinanza'] = cittadinanza_match.group(1)

        # Comune di rilascio
        comune_match = re.search(r'COMUNE\s+DI[:\s]*([A-Z\s]+?)(?:\n|DATA|$)', text_upper)
        if comune_match:
            result['comune_rilascio'] = self._clean_text(comune_match.group(1))

        # Data rilascio
        rilascio_patterns = [
            r'DATA\s+(?:DI\s+)?RILASCIO[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
            r'RILASCIO[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})'
        ]
        result['data_rilascio'] = self._extract_date(text_upper, rilascio_patterns)

        # Data scadenza
        scadenza_patterns = [
            r'DATA\s+(?:DI\s+)?SCADENZA[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
            r'SCADENZA[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
            r'VALIDA\s+FINO\s+AL[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})'
        ]
        result['data_scadenza'] = self._extract_date(text_upper, scadenza_patterns)

        # Numero carta (vari formati)
        numero_patterns = [
            r'(?:N\.|NUMERO|NR\.?|CARTA)[:\s]*([A-Z]{2}\s*\d{5,7}[A-Z]{2})',
            r'(?:N\.|NUMERO|NR\.?)[:\s]*([A-Z0-9]{8,10})',
            r'([A-Z]{2}\d{7}[A-Z]{2})'  # Formato tipo CA1234567AB
        ]
        for pattern in numero_patterns:
            numero_match = re.search(pattern, text_upper)
            if numero_match:
                result['numero_carta'] = self._clean_text(numero_match.group(1))
                break

        # Codice Fiscale
        cf_match = re.search(r'([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])', text_upper)
        if cf_match:
            result['codice_fiscale'] = cf_match.group(1)

        return result

    def _empty_result(self) -> Dict[str, Any]:
        return {
            'nome': None,
            'cognome': None,
            'data_nascita': None,
            'luogo_nascita': None,
            'sesso': None,
            'statura': None,
            'cittadinanza': None,
            'comune_rilascio': None,
            'data_rilascio': None,
            'data_scadenza': None,
            'numero_carta': None,
            'codice_fiscale': None,
            'raw_text': None,
            'error': 'Impossibile estrarre dati'
        }


class CodiceFiscaleExtractor(BaseExtractor):
    """Estrattore per Codice Fiscale"""

    def _parse_text(self, text: str) -> Dict[str, Any]:
        """Parsing specifico per codice fiscale"""

        result = {
            'codice_fiscale': None,
            'cognome_code': None,
            'nome_code': None,
            'anno_nascita': None,
            'mese_nascita': None,
            'giorno_nascita': None,
            'sesso': None,
            'comune_nascita': None,
            'valido': False,
            'raw_text': text
        }

        text_upper = text.upper()

        # Cerca codice fiscale (16 caratteri)
        cf_match = re.search(r'([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])', text_upper)

        if cf_match:
            cf = cf_match.group(1)
            result['codice_fiscale'] = cf

            # Decodifica codice fiscale
            result['cognome_code'] = cf[0:3]
            result['nome_code'] = cf[3:6]
            result['anno_nascita'] = '19' + cf[6:8] if int(cf[6:8]) > 30 else '20' + cf[6:8]

            # Mese di nascita
            mesi = {'A': '01', 'B': '02', 'C': '03', 'D': '04', 'E': '05', 'H': '06',
                   'L': '07', 'M': '08', 'P': '09', 'R': '10', 'S': '11', 'T': '12'}
            result['mese_nascita'] = mesi.get(cf[8], None)

            # Giorno e sesso
            giorno = int(cf[9:11])
            if giorno > 40:
                result['sesso'] = 'F'
                result['giorno_nascita'] = str(giorno - 40).zfill(2)
            else:
                result['sesso'] = 'M'
                result['giorno_nascita'] = str(giorno).zfill(2)

            # Codice comune
            result['comune_nascita'] = cf[11:15]

            # Validazione
            result['valido'] = self.validate_external_codice(cf)

        return result

    def validate_external_codice(self, codice_fiscale: str) -> bool:
        """Valida un codice fiscale"""
        if not codice_fiscale or len(codice_fiscale) != 16:
            return False

        # Pattern base
        if not re.match(r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$', codice_fiscale.upper()):
            return False

        # Controllo carattere di controllo
        odd_map = {
            '0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
            'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
            'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11, 'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
            'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23
        }

        even_map = {
            '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
            'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18,
            'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25
        }

        cf = codice_fiscale.upper()
        total = 0

        for i in range(15):
            char = cf[i]
            if i % 2 == 0:  # Posizione dispari (1-based)
                total += odd_map.get(char, 0)
            else:  # Posizione pari
                total += even_map.get(char, 0)

        check_char = chr(65 + (total % 26))

        return check_char == cf[15]

    def decode_external_codice(self, codice_fiscale: str) -> Dict[str, Any]:
        """Decodifica un codice fiscale esterno"""
        result = self._parse_text(codice_fiscale)
        return result

    def _empty_result(self) -> Dict[str, Any]:
        return {
            'codice_fiscale': None,
            'cognome_code': None,
            'nome_code': None,
            'anno_nascita': None,
            'mese_nascita': None,
            'giorno_nascita': None,
            'sesso': None,
            'comune_nascita': None,
            'valido': False,
            'raw_text': None,
            'error': 'Impossibile estrarre codice fiscale'
        }


class PassaportoExtractor(BaseExtractor):
    """Estrattore per Passaporto italiano"""

    def _parse_text(self, text: str) -> Dict[str, Any]:
        """Parsing specifico per passaporto"""

        result = {
            'tipo_documento': 'PASSAPORTO',
            'codice_stato': None,
            'numero_passaporto': None,
            'cognome': None,
            'nome': None,
            'cittadinanza': None,
            'data_nascita': None,
            'sesso': None,
            'luogo_nascita': None,
            'data_rilascio': None,
            'data_scadenza': None,
            'autorita_rilascio': None,
            'mrz_line1': None,
            'mrz_line2': None,
            'raw_text': text
        }

        text_upper = text.upper()
        lines = text.split('\n')

        # MRZ (Machine Readable Zone) - 2 righe da 44 caratteri
        mrz_lines = []
        for line in lines:
            # Cerca righe che sembrano MRZ
            clean_line = re.sub(r'[^A-Z0-9<]', '', line.upper())
            if len(clean_line) >= 40 and '<' in clean_line:
                mrz_lines.append(clean_line)

        if len(mrz_lines) >= 2:
            result['mrz_line1'] = mrz_lines[0]
            result['mrz_line2'] = mrz_lines[1]

            # Parsing MRZ
            mrz_data = self._parse_mrz(mrz_lines[0], mrz_lines[1])
            result.update(mrz_data)

        # Se non c'è MRZ, prova parsing testuale
        if not result['numero_passaporto']:
            # Numero passaporto
            numero_match = re.search(r'(?:PASSAPORTO|PASSPORT)\s*(?:N\.|NR\.?|NUMERO)?[:\s]*([A-Z0-9]{6,9})', text_upper)
            if numero_match:
                result['numero_passaporto'] = numero_match.group(1)

        if not result['cognome']:
            # Cognome
            cognome_match = re.search(r'(?:COGNOME|SURNAME)[:\s]*([A-Z\s]+?)(?:\n|NOME|$)', text_upper)
            if cognome_match:
                result['cognome'] = self._clean_text(cognome_match.group(1))

        if not result['nome']:
            # Nome
            nome_match = re.search(r'(?:NOME|NAME|GIVEN NAMES)[:\s]*([A-Z\s]+?)(?:\n|DATA|NASC|$)', text_upper)
            if nome_match:
                result['nome'] = self._clean_text(nome_match.group(1))

        # Data nascita
        if not result['data_nascita']:
            nascita_patterns = [
                r'DATA\s+DI\s+NASCITA[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
                r'DATE\s+OF\s+BIRTH[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
                r'NASC[A-Z]*[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})'
            ]
            result['data_nascita'] = self._extract_date(text_upper, nascita_patterns)

        # Sesso
        if not result['sesso']:
            sesso_match = re.search(r'(?:SESSO|SEX)[:\s]*([MF])', text_upper)
            if sesso_match:
                result['sesso'] = sesso_match.group(1)

        # Data rilascio
        if not result['data_rilascio']:
            rilascio_patterns = [
                r'DATA\s+DI\s+RILASCIO[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
                r'DATE\s+OF\s+ISSUE[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
                r'RILASCIO[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})'
            ]
            result['data_rilascio'] = self._extract_date(text_upper, rilascio_patterns)

        # Data scadenza
        if not result['data_scadenza']:
            scadenza_patterns = [
                r'DATA\s+DI\s+SCADENZA[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
                r'DATE\s+OF\s+EXPIRY[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})',
                r'SCADENZA[:\s]*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})'
            ]
            result['data_scadenza'] = self._extract_date(text_upper, scadenza_patterns)

        # Cittadinanza
        if not result['cittadinanza']:
            result['cittadinanza'] = 'ITA'  # Default per passaporto italiano

        return result

    def _parse_mrz(self, line1: str, line2: str) -> Dict[str, Any]:
        """
        Parsing della Machine Readable Zone del passaporto

        Formato MRZ passaporto (TD-3):
        Linea 1: P<CODICE_STATO<COGNOME<<NOME<<<<<<<<<<<<<<<<<<<<
        Linea 2: NUMERO_PASSAPORTO<CHECK<NAZIONE<DATA_NASCITA<CHECK<SESSO<DATA_SCADENZA<CHECK<<<<<<<<<<<<<<<
        """
        result = {}

        try:
            # Linea 1
            if line1.startswith('P<'):
                # Codice stato (caratteri 3-4)
                result['codice_stato'] = line1[2:5].replace('<', '').strip()

                # Nome e cognome
                name_part = line1[5:].split('<<')
                if len(name_part) >= 2:
                    result['cognome'] = name_part[0].replace('<', ' ').strip()
                    result['nome'] = name_part[1].replace('<', ' ').strip()

            # Linea 2
            if len(line2) >= 44:
                # Numero passaporto (posizioni 0-8)
                result['numero_passaporto'] = line2[0:9].replace('<', '').strip()

                # Nazione (posizioni 10-12)
                result['cittadinanza'] = line2[10:13].replace('<', '').strip()

                # Data nascita YYMMDD (posizioni 13-18)
                data_nascita_raw = line2[13:19]
                if data_nascita_raw.isdigit():
                    yy = data_nascita_raw[0:2]
                    mm = data_nascita_raw[2:4]
                    dd = data_nascita_raw[4:6]
                    year = '19' + yy if int(yy) > 30 else '20' + yy
                    result['data_nascita'] = f"{dd}/{mm}/{year}"

                # Sesso (posizione 20)
                result['sesso'] = line2[20] if line2[20] in ['M', 'F'] else None

                # Data scadenza YYMMDD (posizioni 21-26)
                data_scadenza_raw = line2[21:27]
                if data_scadenza_raw.isdigit():
                    yy = data_scadenza_raw[0:2]
                    mm = data_scadenza_raw[2:4]
                    dd = data_scadenza_raw[4:6]
                    year = '20' + yy
                    result['data_scadenza'] = f"{dd}/{mm}/{year}"

        except Exception as e:
            self.logger.warning(f"Errore nel parsing MRZ: {e}")

        return result

    def _empty_result(self) -> Dict[str, Any]:
        return {
            'tipo_documento': 'PASSAPORTO',
            'codice_stato': None,
            'numero_passaporto': None,
            'cognome': None,
            'nome': None,
            'cittadinanza': None,
            'data_nascita': None,
            'sesso': None,
            'luogo_nascita': None,
            'data_rilascio': None,
            'data_scadenza': None,
            'autorita_rilascio': None,
            'mrz_line1': None,
            'mrz_line2': None,
            'raw_text': None,
            'error': 'Impossibile estrarre dati'
        }


# Test
if __name__ == "__main__":
    print("OCR Extractor - Test")
    print("=" * 60)

    # Test estrattori
    carta_ext = CartaIdentitaExtractor()
    cf_ext = CodiceFiscaleExtractor()
    pass_ext = PassaportoExtractor()

    print("\n✓ Estrattori inizializzati correttamente")
    print("  - CartaIdentitaExtractor")
    print("  - CodiceFiscaleExtractor")
    print("  - PassaportoExtractor")

    # Test validazione CF
    test_cf = "RSSMRA85T10A562S"
    print(f"\n✓ Test validazione Codice Fiscale: {test_cf}")
    is_valid = cf_ext.validate_external_codice(test_cf)
    print(f"  Valido: {is_valid}")

    if is_valid:
        decoded = cf_ext.decode_external_codice(test_cf)
        print(f"  Decodifica:")
        print(f"    - Sesso: {decoded['sesso']}")
        print(f"    - Anno: {decoded['anno_nascita']}")
        print(f"    - Mese: {decoded['mese_nascita']}")
        print(f"    - Giorno: {decoded['giorno_nascita']}")

    print("\n" + "=" * 60)
    print("Modulo pronto per l'uso!")
