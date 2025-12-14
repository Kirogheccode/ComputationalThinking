import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, time

# --- 1. PRE-IMPORT SETUP ---
# We must set these dummy variables BEFORE importing the module.
# Otherwise, Search_Clone_2.py will print "Error..." and exit() immediately.
os.environ["GOOGLE_API_KEY"] = "TEST_KEY"
os.environ["GEOAPIFY_API_KEY"] = "TEST_KEY"
os.environ["SPOONACULAR_API_KEY"] = "TEST_KEY"

# Add current directory to path to find the module
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    import Search_Clone_2
except ImportError:
    # Fallback if running from a different directory depth
    sys.path.append(os.path.join(current_dir, '..'))
    import Search_Clone_2


# Helper Class for Gemini Responses
class MockGeminiResponse:
    def __init__(self, text_content):
        self.text = text_content


class TestSearchClone(unittest.TestCase):

    # =========================================================================
    # A. HELPER FUNCTIONS (Logic & Math)
    # =========================================================================

    def test_haversine(self):
        """Test the distance calculation logic."""
        # Distance between Ho Chi Minh City (10.76, 106.66) and Hanoi (21.02, 105.83) ~1137km
        dist = Search_Clone_2.haversine(10.762622, 106.660172, 21.028511, 105.854164)
        self.assertTrue(1100 < dist < 1200, f"Distance {dist} seems wrong")

        # Distance to self should be 0
        self.assertEqual(Search_Clone_2.haversine(10, 10, 10, 10), 0)

    def test_get_bounding_box(self):
        """Test if bounding box math is logically consistent."""
        lat, lon = 10.0, 106.0
        bbox = Search_Clone_2.get_bounding_box(lat, lon, 10)  # 10km radius

        self.assertLess(bbox['min_lat'], lat)
        self.assertGreater(bbox['max_lat'], lat)
        self.assertLess(bbox['min_lon'], lon)
        self.assertGreater(bbox['max_lon'], lon)

    def test_is_open_now(self):
        """Test opening hours logic by mocking 'datetime.now'."""

        # Patch the datetime class imported inside Search_Clone_2
        with patch('Search_Clone_2.datetime') as mock_dt:
            # 1. Simulate Current Time: 10:00 AM
            mock_dt.now.return_value.time.return_value = time(10, 0)
            mock_dt.strptime.side_effect = datetime.strptime  # Use real strptime logic

            # Case: 09:00 - 22:00 -> Should be OPEN
            self.assertTrue(Search_Clone_2.is_open_now("09:00 - 22:00"))

            # Case: 17:00 - 22:00 -> Should be CLOSED
            self.assertFalse(Search_Clone_2.is_open_now("17:00 - 22:00"))

            # Case: 08:00 - 02:00 (Next day) -> Should be OPEN
            self.assertTrue(Search_Clone_2.is_open_now("08:00 - 02:00"))

        # Test invalid inputs (should default to True/Open)
        self.assertTrue(Search_Clone_2.is_open_now("Updating"))
        self.assertTrue(Search_Clone_2.is_open_now(None))

    # =========================================================================
    # B. API WRAPPERS (Mocking Requests)
    # =========================================================================

    @patch('Search_Clone_2.requests.get')
    def test_get_coords_for_location(self, mock_get):
        """Test Geoapify integration."""
        # Setup Mock Response
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            'features': [{'geometry': {'coordinates': [106.123, 10.456]}}]  # [Lon, Lat]
        }
        mock_get.return_value = mock_resp

        # Call function
        lat, lon = Search_Clone_2.get_coords_for_location("District 1")

        self.assertEqual(lat, 10.456)
        self.assertEqual(lon, 106.123)

    @patch('Search_Clone_2.requests.get')
    def test_get_nutrition_spoonacular(self, mock_get):
        """Test Spoonacular integration."""
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
    # C. CORE HANDLERS (Mocking Gemini & Database)
    # =========================================================================

    @patch('google.generativeai.GenerativeModel')
    def test_route_user_request(self, mock_model_cls):
        """Test the intent router (AI)."""
        # Mock AI returning JSON
        mock_json = json.dumps({
            "task": "restaurant_recommendation",
            "location": "District 1",
            "cuisine": "Pho"
        })
        mock_model_cls.return_value.generate_content.return_value = MockGeminiResponse(mock_json)

        res = Search_Clone_2.route_user_request("Where to eat Pho in District 1?")

        self.assertEqual(res['task'], 'restaurant_recommendation')
        self.assertEqual(res['location'], 'District 1')

    @patch('google.generativeai.GenerativeModel')
    def test_handle_culture_query(self, mock_model_cls):
        """Test simple culture query."""
        mock_model_cls.return_value.generate_content.return_value = MockGeminiResponse("This is Tet holiday.")

        res = Search_Clone_2.handle_culture_query("What is Tet?")
        self.assertEqual(res, "This is Tet holiday.")

    @patch('Search_Clone_2.sqlite3.connect')
    @patch('Search_Clone_2.get_coords_for_location')
    @patch('google.generativeai.GenerativeModel')
    def test_handle_restaurant_recommendation(self, mock_genai, mock_geo, mock_sql):
        """Test restaurant search: Geocode -> DB -> AI Ranking."""
        # 1. Mock Geocoding
        mock_geo.return_value = (10.0, 100.0)

        # 2. Mock Database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sql.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # --- FIX: Change name to include 'Food' so it matches the search query ---
        mock_row = {
            'name': 'Test Food Resto',  # Changed from 'Test Resto'
            'latitude': 10.0, 'longitude': 100.0,
            'opening_hours': '08:00 - 22:00',
            'rating': 5.0
        }
        mock_cursor.fetchall.return_value = [mock_row]

        # 3. Mock AI Final Response
        final_json = json.dumps({
            "explanation": "Here is a place",
            "recommendations": [{"Name": "Test Food Resto", "Address": "123 St"}]
        })
        mock_genai.return_value.generate_content.return_value = MockGeminiResponse(final_json)

        # Execute
        # Search query is 'food', so mock data must contain 'food'
        entities = {'location': 'here', 'cuisine': 'food'}
        result = Search_Clone_2.handle_restaurant_recommendation("Find food", entities)

        # Assert
        # Now result is a Dict because we didn't hit the fallback
        self.assertEqual(result['text'], "Here is a place")
        self.assertEqual(len(result['restaurants']), 1)

    @patch('google.generativeai.GenerativeModel')
    @patch('Search_Clone_2.get_nutrition_from_spoonacular')
    def test_handle_daily_menu(self, mock_spoon, mock_genai):
        """Test daily menu: AI JSON -> Spoonacular -> Result."""

        # 1. Mock AI (First call only)
        # The function generates a JSON menu plan
        menu_json = json.dumps({
            "explanation": "Healthy plan",
            "recommendations": [
                {"MainMeal": "Breakfast", "FoodName": "Pho"}
            ]
        })
        mock_genai.return_value.generate_content.return_value = MockGeminiResponse(menu_json)

        # 2. Mock Spoonacular (Helper function)
        mock_spoon.return_value = {"Calories": "300 kcal", "Protein": "10 g", "Fat": "5 g"}

        # Execute
        res = Search_Clone_2.handle_daily_menu("Plan diet", {'budget': 'low'})

        # Assert
        self.assertEqual(res['text'], "Healthy plan")
        self.assertEqual(res['menu'][0]['Calories'], "300 kcal")
        mock_spoon.assert_called_with("Pho")

    # =========================================================================
    # D. MAIN INTEGRATION (replyToUser)
    # =========================================================================

    @patch('Search_Clone_2.route_user_request')
    @patch('Search_Clone_2.handle_restaurant_recommendation')
    def test_replyToUser_restaurant(self, mock_handler, mock_router):
        """Test the main entry point for restaurant flow."""
        # 1. Mock Router to return restaurant task
        mock_router.return_value = {
            "task": "restaurant_recommendation",
            "mode": "/place_",  # Important: matches logic in replyToUser
            "location": "HCM", "cuisine": "Rice"
        }

        # 2. Mock Handler
        mock_handler.return_value = {"text": "Found it", "restaurants": []}

        # Execute
        data = {"message": "/place_ Rice in HCM", "mode": "/place_"}
        result = Search_Clone_2.replyToUser(data)

        # Assert
        self.assertEqual(result['reply'], "Found it")
        mock_handler.assert_called()

    @patch('Search_Clone_2.route_user_request')
    @patch('Search_Clone_2.handle_culture_query')
    def test_replyToUser_culture(self, mock_handler, mock_router):
        """Test fallback to culture query."""
        # If no mode is provided or empty mode
        mock_router.return_value = {"task": "culture_query"}
        mock_handler.return_value = "Cultural Info"

        data = {"message": "What is Pho?", "mode": ""}
        result = Search_Clone_2.replyToUser(data)

        self.assertEqual(result['reply'], "Cultural Info")


if __name__ == '__main__':
    unittest.main()