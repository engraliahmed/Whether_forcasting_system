import unittest
from unittest.mock import patch, MagicMock
from weather_forecast_app import WeatherData, DatabaseManager

class TestWeatherData(unittest.TestCase):
    def setUp(self):
        self.api_key = "dummy_key"
        self.weather = WeatherData(self.api_key)

    @patch('weather_forecast_app.requests.get')
    def test_fetch_weather_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "cod": 200,
            "name": "Lahore",
            "main": {"temp": 30, "humidity": 50},
            "wind": {"speed": 2},
            "weather": [{"description": "clear sky"}],
            "coord": {"lat": 31.5, "lon": 74.3}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        data, error = self.weather.fetch_weather(city="Lahore")
        self.assertIsNone(error)
        self.assertEqual(data["city"], "Lahore")
        self.assertEqual(data["temp"], 30)

    @patch('weather_forecast_app.requests.get')
    def test_fetch_weather_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"cod": 404, "message": "city not found"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        data, error = self.weather.fetch_weather(city="FakeCity")
        self.assertIsNone(data)
        self.assertIn("city not found", error)

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")  # Use in-memory DB for testing

    def tearDown(self):
        self.db.close()

    def test_add_and_remove_favorite(self):
        success, msg = self.db.add_favorite("Lahore", 31.5, 74.3)
        self.assertTrue(success)
        favs = self.db.get_favorites()
        self.assertEqual(len(favs), 1)
        self.assertEqual(favs[0][0], "Lahore")
        success, msg = self.db.remove_favorite("Lahore")
        self.assertTrue(success)
        favs = self.db.get_favorites()
        self.assertEqual(len(favs), 0)

    def test_save_and_get_weather_history(self):
        weather_data = {
            "city": "Lahore",
            "temp": 30,
            "humidity": 50,
            "wind_speed": 2,
            "description": "clear sky",
            "timestamp": "2025-06-13 12:00:00"
        }
        self.db.save_weather_history(weather_data)
        history = self.db.get_weather_history("Lahore")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][0], 30)
        self.assertEqual(history[0][1], 50)

if __name__ == "__main__":
    unittest.main()
