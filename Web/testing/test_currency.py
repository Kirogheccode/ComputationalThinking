import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# --- 1. SETUP ENVIRONMENT ---
# Set dummy keys BEFORE importing Currency.py so it initializes variables correctly
os.environ["CURRENCY_API_KEY"] = "TEST_CURRENCY_KEY"
os.environ["GOOGLE_API_KEY"] = "TEST_GOOGLE_KEY"

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    import Currency
except ImportError:
    sys.path.append(os.path.join(current_dir, '..'))
    import Currency

class TestCurrency(unittest.TestCase):

    # =========================================================================
    # A. TEST EXCHANGE RATE API (get_exchange_rate)
    # =========================================================================

    @patch('Currency.requests.get')
    def test_get_exchange_rate_success(self, mock_get):
        """Test successful API call."""
        # 1. Setup Mock Response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": "success",
            "conversion_rate": 25000.0
        }
        mock_get.return_value = mock_response

        # 2. Execute
        result = Currency.get_exchange_rate("USD")

        # 3. Assert
        self.assertTrue(result['success'])
        self.assertEqual(result['rate'], 25000.0)
        self.assertEqual(result['name'], "United States Dollar")
        # Ensure URL was constructed correctly with the dummy key
        expected_url = "https://v6.exchangerate-api.com/v6/TEST_CURRENCY_KEY/pair/USD/VND"
        mock_get.assert_called_with(expected_url)

    @patch('Currency.requests.get')
    def test_get_exchange_rate_api_error(self, mock_get):
        """Test API returning an error (e.g., invalid key)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": "error",
            "error-type": "invalid-key"
        }
        mock_get.return_value = mock_response

        result = Currency.get_exchange_rate("USD")

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "invalid-key")

    @patch('Currency.requests.get')
    def test_get_exchange_rate_exception(self, mock_get):
        """Test network exception (e.g., no internet)."""
        mock_get.side_effect = Exception("Network Down")

        result = Currency.get_exchange_rate("USD")

        self.assertFalse(result['success'])
        self.assertIn("Network Down", result['error'])

    # =========================================================================
    # B. TEST CALCULATION LOGIC (calculate_conversion)
    # =========================================================================

    @patch('Currency.get_exchange_rate')
    def test_calculate_conversion_foreign_to_vnd(self, mock_get_rate):
        """Test converting USD to VND (Direction '1')."""
        # Mock rate as 25,000 VND per USD
        mock_get_rate.return_value = {"success": True, "rate": 25000.0}

        # Convert 10 USD
        result = Currency.calculate_conversion(10, "USD", '1')

        self.assertTrue(result['success'])
        self.assertEqual(result['original_amount'], 10)
        # 10 * 25,000 = 250,000
        self.assertEqual(result['converted_string'], "250,000 VND")
        self.assertIn("1 USD = 25,000 VND", result['rate_display'])

    @patch('Currency.get_exchange_rate')
    def test_calculate_conversion_vnd_to_foreign(self, mock_get_rate):
        """Test converting VND to USD (Direction '2')."""
        # Mock rate as 25,000 VND per USD
        mock_get_rate.return_value = {"success": True, "rate": 25000.0}

        # Convert 50,000 VND
        result = Currency.calculate_conversion(50000, "USD", '2')

        self.assertTrue(result['success'])
        # 50,000 / 25,000 = 2.00
        self.assertEqual(result['converted_string'], "2.00 USD")
        self.assertIn("1 VND ≈ 0.000040 USD", result['rate_display'])

    @patch('Currency.get_exchange_rate')
    def test_calculate_conversion_api_fail(self, mock_get_rate):
        """Test behavior when API fails."""
        mock_get_rate.return_value = {"success": False, "error": "API Error"}

        result = Currency.calculate_conversion(100, "USD", '1')

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "API Error")

    # =========================================================================
    # C. TEST GEMINI VISION (scan_money_image)
    # =========================================================================

    @patch('Currency.genai')
    def test_scan_money_success(self, mock_genai):
        """Test successfully analyzing a single bill."""
        # 1. Setup Mock Model Response
        mock_model_instance = mock_genai.GenerativeModel.return_value
        
        # Simulating valid JSON response from Gemini
        mock_json_response = json.dumps({
            "amount": 100,
            "currency": "USD",
            "item_count": 1,
            "warning": None
        })
        
        # The .text property of the response object
        mock_response_object = MagicMock()
        mock_response_object.text = f"```json\n{mock_json_response}\n```"
        mock_model_instance.generate_content.return_value = mock_response_object

        # 2. Execute
        result = Currency.scan_money_image("dummy_path.jpg")

        # 3. Assert
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['amount'], 100)
        self.assertEqual(result['data']['currency'], "USD")
        
        # Ensure upload_file was called
        mock_genai.upload_file.assert_called_with(path="dummy_path.jpg", display_name="User Money Upload")

    @patch('Currency.genai')
    def test_scan_money_multiple_items_detected(self, mock_genai):
        """Test strict mode: Reject if multiple items are found."""
        mock_model_instance = mock_genai.GenerativeModel.return_value
        
        # Gemini says there are 2 bills
        mock_json_response = json.dumps({
            "amount": 200,
            "currency": "USD",
            "item_count": 2 
        })
        
        mock_response_object = MagicMock()
        mock_response_object.text = mock_json_response
        mock_model_instance.generate_content.return_value = mock_response_object

        result = Currency.scan_money_image("dummy_path.jpg")

        # Should fail due to item_count > 1
        self.assertFalse(result['success'])
        self.assertIn("Detected 2 items", result['error'])

    @patch('Currency.genai')
    def test_scan_money_gemini_error(self, mock_genai):
        """Test when Gemini throws an exception."""
        mock_model_instance = mock_genai.GenerativeModel.return_value
        mock_model_instance.generate_content.side_effect = Exception("API Overloaded")

        result = Currency.scan_money_image("dummy_path.jpg")

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Could not recognize money in this image.")

if __name__ == '__main__':
    unittest.main()