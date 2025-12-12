import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
import json
import sys
import os

# Thêm thư mục cha vào sys.path để import được Routing.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import Routing

class TestRoutingEdgeCases(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Định nghĩa các hằng số toạ độ
        self.COORD_HCM = (10.7625844, 106.68169483128824)
        self.COORD_AMBIGUOUS = (13.7569509, 109.21463)
        self.COORD_FAKE = (21.121006616308723, 105.96504611292063)
        self.COORD_NUMBER = (10.0, 100.0)
        self.COORD_ITALY = (45.46283285, 9.155790632322352)

        # Địa chỉ mẫu cho 5 test cases
        # 1. Địa chỉ đi là số
        # 2. Địa chỉ đến là chuỗi lạ
        # 3. Địa chỉ đi và đến giống nhau
        # 4. Địa chỉ đến mơ hồ
        # 5. Địa chỉ đến không tồn tại
        # 6. Địa chỉ không thể đi (HCM -> Italy)
        self.ADDR_HCM = "Đại Học Khoa Học Tự Nhiên - 227 Nguyễn Văn Cừ, P4, Q5, TP.HCM"
        self.ADDR_AMBIGUOUS = "Nguyễn Văn Cừ"
        self.ADDR_FAKE = "189 Nguyễn Lê Hoàng Khải"
        self.ADDR_WEIRD = "skibidi dop dop"
        self.ADDR_ITALY = "Via Sardegna, 45, 20146 Milano MI, Italy"

    def tearDown(self):
        self.ctx.pop()

    def mock_geocode_side_effect(self, address):
        if address == self.ADDR_HCM:
            return self.COORD_HCM
        elif address == self.ADDR_AMBIGUOUS:
            return self.COORD_AMBIGUOUS
        elif address == self.ADDR_FAKE:
            return self.COORD_FAKE
        elif address == self.ADDR_ITALY:
            return self.COORD_ITALY
        elif address.isdigit() or address == "-123" or address == self.ADDR_WEIRD: 
            return self.COORD_NUMBER
        return None, None

    @patch('Routing.get_route')
    @patch('Routing.get_coordinates_from_db')
    @patch('Routing.geocode_address')
    def test_case_1_origin_is_number(self, mock_geocode, mock_db, mock_route):
        """
        Case 1: Nhập địa chỉ là số bất kỳ.
        Kỳ vọng: Trả về thông báo lỗi cho người dùng.
        """
        data = {
            'origin': '12345',
            'destination': self.ADDR_HCM
        }
        
        result = Routing.drawPathToDestionation(data)
        
        if isinstance(result, tuple):
            response, status_code = result
        else:
            response = result
            status_code = 200

        self.assertEqual(status_code, 400)
        json_data = response.get_json()
        
        self.assertIn("không hợp lệ", json_data['error'])

    @patch('Routing.get_route')
    @patch('Routing.get_coordinates_from_db')
    @patch('Routing.geocode_address')
    def test_case_2_destination_is_weird_string(self, mock_geocode, mock_db, mock_route):
        """
        Case 2: Nhập địa chỉ là chuỗi lạ.
        Kỳ vọng: Trả về thông báo lỗi cho người dùng.
        """
        mock_geocode.side_effect = self.mock_geocode_side_effect
        mock_db.return_value = (None, None) 
        mock_route.return_value = {"type": "LineString", "coordinates": []} 

        data = {
            'origin': self.ADDR_HCM,
            'destination': self.ADDR_WEIRD
        }

        response = Routing.drawPathToDestionation(data)
        
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['end_point'], list(self.COORD_NUMBER))

    @patch('Routing.get_route')
    @patch('Routing.get_coordinates_from_db')
    @patch('Routing.geocode_address')
    def test_case_3_same_address(self, mock_geocode, mock_db, mock_route):
        """
        Case 3: Nhập địa chỉ đi và đến giống nhau (Đại Học Khoa Học Tự Nhiên - 227 Nguyễn Văn Cừ, P4, Q5, TP.HCM).
        Kỳ vọng: Chạy bình thường.
        """
        mock_geocode.side_effect = self.mock_geocode_side_effect
        mock_db.return_value = (None, None)
        mock_route.return_value = {"type": "LineString", "coordinates": []}

        data = {'origin': self.ADDR_HCM, 'destination': self.ADDR_HCM}
        response = Routing.drawPathToDestionation(data)
        
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['start_point'], list(self.COORD_HCM))
        self.assertEqual(json_data['end_point'], list(self.COORD_HCM))

    @patch('Routing.get_route')
    @patch('Routing.get_coordinates_from_db')
    @patch('Routing.geocode_address')
    def test_case_4_ambiguous_destination(self, mock_geocode, mock_db, mock_route):
        """
        Case 4: Nhập địa không rõ ràng (Nguyễn Văn Cừ).
        Kỳ vọng: Trả về toạ độ phù hợp nhất với địa chỉ.
        """
        mock_geocode.side_effect = self.mock_geocode_side_effect
        mock_db.return_value = (None, None)
        mock_route.return_value = {"type": "LineString", "coordinates": []}

        data = {'origin': self.ADDR_HCM, 'destination': self.ADDR_AMBIGUOUS}
        response = Routing.drawPathToDestionation(data)
        
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['end_point'], list(self.COORD_AMBIGUOUS))

    @patch('Routing.get_route')
    @patch('Routing.get_coordinates_from_db')
    @patch('Routing.geocode_address')
    def test_case_5_non_existent_destination(self, mock_geocode, mock_db, mock_route):
        """
        Case 5: Nhập địa không tồn tại trên bản đồ (189 Nguyễn Lê Hoàng Khải).
        Kỳ vọng: Trả về toạ độ phù hợp nhất với địa chỉ.
        """
        mock_geocode.side_effect = self.mock_geocode_side_effect
        mock_db.return_value = (None, None)
        mock_route.return_value = {"type": "LineString", "coordinates": []}

        data = {'origin': self.ADDR_HCM, 'destination': self.ADDR_FAKE}
        response = Routing.drawPathToDestionation(data)
        
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['end_point'], list(self.COORD_FAKE))

    @patch('Routing.get_route')
    @patch('Routing.get_coordinates_from_db')
    @patch('Routing.geocode_address')
    def test_case_6_impossible_route(self, mock_geocode, mock_db, mock_route):
        """
        Case 6: Đi từ VN sang Ý (Impossible Route).
        Kỳ vọng: Routing.py bắt Exception từ ORS và trả về 500.
        """
        mock_geocode.side_effect = self.mock_geocode_side_effect
        mock_db.return_value = (None, None)
        
        mock_route.side_effect = Exception("OpenRouteService: Cannot find route")

        data = {'origin': self.ADDR_HCM, 'destination': self.ADDR_ITALY}
        
        result = Routing.drawPathToDestionation(data)
        
        if isinstance(result, tuple):
            response, status_code = result
        else:
            response = result
            status_code = 200
            
        self.assertEqual(status_code, 500)
        json_data = response.get_json()
        self.assertIn("Cannot find route", json_data['error'])

if __name__ == '__main__':
    unittest.main()