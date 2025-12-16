import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, time

# --- 1. SETUP ENVIRONMENT ---
os.environ["GOOGLE_API_KEY"] = "TEST_KEY"
os.environ["GEOAPIFY_API_KEY"] = "TEST_KEY"
os.environ["SPOONACULAR_API_KEY"] = "TEST_KEY"

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- MOCK MISSING MODULES (Prevents ImportError) ---
sys.modules["pymongo"] = MagicMock()
sys.modules["SaveAnswer"] = MagicMock()

# --- IMPORT MODULE UNDER TEST ---
try:
    import Search_Clone_2
except ImportError:
    sys.path.append(os.path.join(current_dir, '..'))
    import Search_Clone_2


# Helper Class
class MockGeminiResponse:
    def __init__(self, text_content):
        self.text = text_content


class TestSearchClone(unittest.TestCase):

    # =========================================================================
    # A. HELPER FUNCTIONS
    # =========================================================================

    def test_haversine(self):
        """Test distance calculation."""
        dist = Search_Clone_2.haversine(10.762622, 106.660172, 21.028511, 105.854164)
        self.assertTrue(1100 < dist < 1200)
        self.assertEqual(Search_Clone_2.haversine(10, 10, 10, 10), 0)

    def test_get_bounding_box(self):
        """Test bounding box."""
        lat, lon = 10.0, 106.0
        bbox = Search_Clone_2.get_bounding_box(lat, lon, 10)
        self.assertLess(bbox['min_lat'], lat)
        self.assertGreater(bbox['max_lat'], lat)

    def test_is_open_now(self):
        """Test opening hours with mocked time."""
        with patch('Search_Clone_2.datetime') as mock_dt:
            # Set time to 10:00 AM
            mock_dt.now.return_value.time.return_value = time(10, 0)
            mock_dt.strptime.side_effect = datetime.strptime

            self.assertTrue(Search_Clone_2.is_open_now("09:00 - 22:00"))
            self.assertFalse(Search_Clone_2.is_open_now("17:00 - 22:00"))
            self.assertTrue(Search_Clone_2.is_open_now("08:00 - 02:00"))

        self.assertTrue(Search_Clone_2.is_open_now("Updating"))
        self.assertTrue(Search_Clone_2.is_open_now(None))

    # =========================================================================
    # B. API WRAPPERS
    # =========================================================================

    @patch('Search_Clone_2.requests.get')
    def test_get_coords_for_location(self, mock_get):
        """Test Geoapify."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            'features': [{'geometry': {'coordinates': [106.123, 10.456]}}]
        }
        mock_get.return_value = mock_resp

        lat, lon = Search_Clone_2.get_coords_for_location("District 1")
        self.assertEqual(lat, 10.456)
        self.assertEqual(lon, 106.123)

    @patch('Search_Clone_2.requests.get')
    def test_get_nutrition_spoonacular(self, mock_get):
        """Test Spoonacular."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [{
                "title": "Pho",
                "nutrition": {"nutrients": [{"name": "Calories", "amount": 300, "unit": "kcal"}]}
            }]
        }
        mock_get.return_value = mock_resp

        result = Search_Clone_2.get_nutrition_from_spoonacular("Pho")
        self.assertIn("300 kcal", result["Calories"])

    # =========================================================================
    # C. CORE HANDLERS
    # =========================================================================

    @patch('google.generativeai.GenerativeModel')
    def test_route_user_request(self, mock_model_cls):
        """Test Intent Router."""
        mock_json = json.dumps({
            "task": "restaurant_recommendation",
            "location": "District 1",
            "cuisine": "Pho"
        })
        mock_model_cls.return_value.generate_content.return_value = MockGeminiResponse(mock_json)

        res = Search_Clone_2.route_user_request("Where to eat Pho in District 1?")
        self.assertEqual(res['task'], 'restaurant_recommendation')

    @patch('google.generativeai.GenerativeModel')
    def test_handle_culture_query(self, mock_model_cls):
        """Test Culture Query."""
        mock_model_cls.return_value.generate_content.return_value = MockGeminiResponse("This is Tet.")
        res = Search_Clone_2.handle_culture_query("What is Tet?")
        self.assertEqual(res, "This is Tet.")

    @patch('Search_Clone_2.sqlite3.connect')
    @patch('Search_Clone_2.get_coords_for_location')
    @patch('google.generativeai.GenerativeModel')
    def test_handle_restaurant_recommendation(self, mock_genai, mock_geo, mock_sql):
        """Test Restaurant Search."""
        mock_geo.return_value = (10.0, 100.0)

        # Mock DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sql.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # NOTE: Name must contain 'food' to match search query
        mock_row = {
            'name': 'Test Food Resto',
            'latitude': 10.0, 'longitude': 100.0,
            'opening_hours': '08:00 - 22:00',
            'rating': 5.0,
            'price_range': '30000-60000',
            'tags': 'Family, Office workers'
        }
        mock_cursor.fetchall.return_value = [mock_row]

        # Mock AI
        final_json = json.dumps({
            "explanation": "Here is a place",
            "recommendations": [{"Name": "Test Food Resto", "Address": "123 St"}]
        })
        mock_genai.return_value.generate_content.return_value = MockGeminiResponse(final_json)

        entities = {'location': 'here', 'cuisine': 'food'}
        result = Search_Clone_2.handle_restaurant_recommendation("Find food", entities)

        self.assertEqual(result['text'], "Here is a place")
        self.assertEqual(len(result['restaurants']), 1)

    @patch('google.generativeai.GenerativeModel')
    @patch('Search_Clone_2.get_nutrition_from_spoonacular')
    def test_handle_daily_menu(self, mock_spoon, mock_genai):
        """Test Daily Menu."""
        menu_json = json.dumps({
            "explanation": "Healthy plan",
            "recommendations": [{"MainMeal": "Breakfast", "FoodName": "Pho"}]
        })
        mock_genai.return_value.generate_content.return_value = MockGeminiResponse(menu_json)
        mock_spoon.return_value = {"Calories": "300 kcal", "Protein": "10 g", "Fat": "5 g"}

        res = Search_Clone_2.handle_daily_menu("Plan diet", {'budget': 'low'})
        self.assertEqual(res['text'], "Healthy plan")

    # =========================================================================
    # D. MAIN INTEGRATION (With Runtime Fix)
    # =========================================================================

    @patch('Search_Clone_2.saveAnswerForUser')  # <--- FIX: Mock the DB saver
    @patch('Search_Clone_2.route_user_request')
    @patch('Search_Clone_2.handle_restaurant_recommendation')
    def test_replyToUser_restaurant(self, mock_handler, mock_router, mock_save_db):
        """Test replyToUser for restaurant."""
        mock_router.return_value = {
            "task": "restaurant_recommendation",
            "mode": "/place_",
            "location": "HCM", "cuisine": "Rice"
        }
        mock_handler.return_value = {"text": "Found it", "restaurants": []}

        data = {"message": "/place_ Rice in HCM", "mode": "/place_"}
        result = Search_Clone_2.replyToUser(data)

        self.assertEqual(result['reply'], "Found it")
        mock_handler.assert_called()
        mock_save_db.assert_called()  # Verifies it tried to save (but to our mock)

    @patch('Search_Clone_2.saveAnswerForUser')  # <--- FIX: Mock the DB saver
    @patch('Search_Clone_2.route_user_request')
    @patch('Search_Clone_2.handle_culture_query')
    def test_replyToUser_culture(self, mock_handler, mock_router, mock_save_db):
        """Test replyToUser for culture."""
        mock_router.return_value = {"task": "culture_query"}
        mock_handler.return_value = "Cultural Info"

        data = {"message": "What is Pho?", "mode": ""}
        result = Search_Clone_2.replyToUser(data)

        self.assertEqual(result['reply'], "Cultural Info")
        mock_save_db.assert_called()


if __name__ == '__main__':
    unittest.main()