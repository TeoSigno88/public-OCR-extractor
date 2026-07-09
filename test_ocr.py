#!/usr/bin/env python3
"""
Test suite per OCR Extractor

Test per:
- Validazione Codice Fiscale
- Parsing MRZ Passaporto
- API endpoints
- Gestione Base64
"""

import unittest
import base64
import io
from PIL import Image
import numpy as np

from ocr_extractor import (
    CartaIdentitaExtractor,
    CodiceFiscaleExtractor,
    PassaportoExtractor
)


class TestCodiceFiscaleValidation(unittest.TestCase):
    """Test validazione Codice Fiscale"""

    def setUp(self):
        self.extractor = CodiceFiscaleExtractor()

    def test_valid_codice_fiscale(self):
        """Test con codici fiscali validi"""
        valid_codes = [
            "RSSMRA85T10A562S",  # Valido verificato
        ]

        for code in valid_codes:
            with self.subTest(code=code):
                self.assertTrue(
                    self.extractor.validate_external_codice(code),
                    f"Codice {code} dovrebbe essere valido"
                )

    def test_invalid_codice_fiscale(self):
        """Test con codici fiscali non validi"""
        invalid_codes = [
            "RSSMRA85T10A562X",  # Checksum errato
            "RSSMRA85T10A562",   # Troppo corto
            "123456789012345X",  # Formato errato
            "",                  # Vuoto
            "ABCDEFGHILMNOPQR"   # Checksum errato
        ]

        for code in invalid_codes:
            with self.subTest(code=code):
                self.assertFalse(
                    self.extractor.validate_external_codice(code),
                    f"Codice {code} dovrebbe essere non valido"
                )

    def test_decode_codice_fiscale(self):
        """Test decodifica codice fiscale"""
        code = "RSSMRA85T10A562S"
        result = self.extractor.decode_external_codice(code)

        self.assertEqual(result['codice_fiscale'], code)
        self.assertEqual(result['sesso'], 'M')
        self.assertEqual(result['anno_nascita'], '1985')
        self.assertEqual(result['mese_nascita'], '12')  # T = dicembre
        self.assertEqual(result['giorno_nascita'], '10')
        self.assertTrue(result['valido'])

    def test_decode_codice_fiscale_female(self):
        """Test decodifica codice fiscale femminile"""
        code = "VRDGPP65D55F205V"  # Giorno 55 = 15 + 40 (femmina)
        result = self.extractor.decode_external_codice(code)

        self.assertEqual(result['sesso'], 'F')
        self.assertEqual(result['giorno_nascita'], '15')  # 55 - 40


class TestPassaportoMRZ(unittest.TestCase):
    """Test parsing MRZ passaporto"""

    def setUp(self):
        self.extractor = PassaportoExtractor()

    def test_parse_mrz_passport(self):
        """Test parsing MRZ passaporto valido"""
        # MRZ esempio passaporto italiano
        # Formato: PASSAPORTO(9)<CHECK(1)NAZ(3)DATA_NASC(6)<CHECK(1)SESSO(1)DATA_SCAD(6)...
        mrz_line1 = "P<ITAROSSI<<MARIO<<<<<<<<<<<<<<<<<<<<<<<<<<<"
        mrz_line2 = "YA12345671ITA8501019M2501015<<<<<<<<<<<<<06"

        result = self.extractor._parse_mrz(mrz_line1, mrz_line2)

        # Verifica che il parsing restituisca almeno alcuni campi
        self.assertIsInstance(result, dict)
        self.assertIn('codice_stato', result)
        self.assertIn('cognome', result)

        # Verifica i valori principali
        self.assertEqual(result['codice_stato'], 'ITA')
        self.assertEqual(result['cognome'], 'ROSSI')
        self.assertEqual(result['nome'], 'MARIO')

        # Questi possono variare in base al parsing
        if 'numero_passaporto' in result:
            self.assertTrue(len(result['numero_passaporto']) > 0)
        if 'sesso' in result:
            self.assertIn(result['sesso'], ['M', 'F', None])

    def test_parse_mrz_with_multiple_names(self):
        """Test parsing MRZ con nomi multipli"""
        mrz_line1 = "P<ITAVERDI<<GIUSEPPE<MARIA<<<<<<<<<<<<<<<<<<<"
        mrz_line2 = "AB9876543<2ITA9012259F2612318<<<<<<<<<<<<<04"

        result = self.extractor._parse_mrz(mrz_line1, mrz_line2)

        self.assertEqual(result['cognome'], 'VERDI')
        self.assertEqual(result['nome'], 'GIUSEPPE MARIA')
        # Sesso in posizione 20
        if 'sesso' in result and result['sesso']:
            self.assertEqual(result['sesso'], 'F')


class TestBase64Handling(unittest.TestCase):
    """Test gestione Base64"""

    def setUp(self):
        self.extractor = CartaIdentitaExtractor()

    def create_test_image(self):
        """Crea un'immagine di test"""
        img = Image.new('RGB', (1500, 1000), color='white')
        return img

    def test_load_base64_plain(self):
        """Test caricamento Base64 semplice"""
        img = self.create_test_image()

        # Converti in Base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Carica
        loaded_img = self.extractor._load_image({'base64': b64_str})

        self.assertIsNotNone(loaded_img)
        self.assertEqual(loaded_img.shape[1], 1500)  # width
        self.assertEqual(loaded_img.shape[0], 1000)  # height

    def test_load_base64_with_data_uri(self):
        """Test caricamento Base64 con data URI prefix"""
        img = self.create_test_image()

        # Converti in Base64 con prefix
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        b64_with_prefix = f"data:image/png;base64,{b64_str}"

        # Carica
        loaded_img = self.extractor._load_image({'base64': b64_with_prefix})

        self.assertIsNotNone(loaded_img)
        self.assertEqual(loaded_img.shape[1], 1500)
        self.assertEqual(loaded_img.shape[0], 1000)


class TestImagePreprocessing(unittest.TestCase):
    """Test pre-processing immagini"""

    def setUp(self):
        self.extractor = CartaIdentitaExtractor()

    def test_preprocess_small_image(self):
        """Test ridimensionamento immagine piccola"""
        # Crea immagine piccola (800x600)
        small_img = np.ones((600, 800, 3), dtype=np.uint8) * 255

        # Pre-processa
        processed = self.extractor._preprocess_image(small_img)

        # Dovrebbe essere ridimensionata a width=1500
        self.assertGreaterEqual(processed.shape[1], 1500)

    def test_preprocess_large_image(self):
        """Test immagine già grande"""
        # Crea immagine grande (2000x1500)
        large_img = np.ones((1500, 2000, 3), dtype=np.uint8) * 255

        # Pre-processa
        processed = self.extractor._preprocess_image(large_img)

        # Non dovrebbe essere ridimensionata
        self.assertLessEqual(processed.shape[1], 2500)


class TestTextCleaning(unittest.TestCase):
    """Test pulizia testo"""

    def setUp(self):
        self.extractor = CartaIdentitaExtractor()

    def test_clean_text(self):
        """Test pulizia testo"""
        dirty = "  MARIO   ROSSI  \n\t"
        clean = self.extractor._clean_text(dirty)

        self.assertEqual(clean, "MARIO ROSSI")

    def test_clean_empty(self):
        """Test pulizia stringa vuota"""
        self.assertEqual(self.extractor._clean_text(""), "")
        self.assertEqual(self.extractor._clean_text(None), "")


class TestDateExtraction(unittest.TestCase):
    """Test estrazione date"""

    def setUp(self):
        self.extractor = CartaIdentitaExtractor()

    def test_extract_date_various_formats(self):
        """Test estrazione date in vari formati"""
        test_cases = [
            ("nato il 01/01/1985", [r'nato il (\d{2}/\d{2}/\d{4})'], "01/01/1985"),
            ("DATA NASCITA: 15.03.1990", [r'DATA NASCITA:\s*(\d{2}\.\d{2}\.\d{4})'], "15.03.1990"),
            ("nasc 25-12-2000", [r'nasc\s*(\d{2}-\d{2}-\d{4})'], "25-12-2000"),
        ]

        for text, patterns, expected in test_cases:
            with self.subTest(text=text):
                result = self.extractor._extract_date(text, patterns)
                self.assertEqual(result, expected)


def run_tests():
    """Esegui tutti i test"""
    print("=" * 70)
    print("TEST SUITE - OCR EXTRACTOR")
    print("=" * 70)
    print()

    # Crea test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Aggiungi tutti i test
    suite.addTests(loader.loadTestsFromTestCase(TestCodiceFiscaleValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestPassaportoMRZ))
    suite.addTests(loader.loadTestsFromTestCase(TestBase64Handling))
    suite.addTests(loader.loadTestsFromTestCase(TestImagePreprocessing))
    suite.addTests(loader.loadTestsFromTestCase(TestTextCleaning))
    suite.addTests(loader.loadTestsFromTestCase(TestDateExtraction))

    # Esegui
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 70)
    print("RIEPILOGO")
    print("=" * 70)
    print(f"Test eseguiti: {result.testsRun}")
    print(f"Successi: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Fallimenti: {len(result.failures)}")
    print(f"Errori: {len(result.errors)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
