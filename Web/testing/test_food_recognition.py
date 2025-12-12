import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
import sys
import os

# Thêm thư mục cha vào sys.path để import được FoodRecognition.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import FoodRecognition

class TestFoodRecognition(unittest.TestCase):

    def setUp(self):
        # Tạo Flask app context
        self.app = Flask(__name__)
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Giả lập dữ liệu bytes cho các bức ảnh
        self.IMG_BYTES_BLUR = b"binary_data_of_pho_blur"
        self.IMG_BYTES_AIRBLADE = b"binary_data_of_airblade"
        self.IMG_BYTES_HIGH_RES = b"binary_data_of_pho_high_res"
        
        # Thêm bytes giả lập cho hình bị lỗi
        self.IMG_BYTES_ERROR = b"binary_data_of_error_picture"

    def tearDown(self):
        self.ctx.pop()

    # Hàm giả lập (Side Effect) cho model.generate_content
    def mock_generate_content_side_effect(self, contents):
        
        input_image_bytes = contents[1]['data']
        
        # Tạo đối tượng response giả
        mock_response = MagicMock()

        if input_image_bytes == self.IMG_BYTES_BLUR:
            mock_response.text = "Phở Bò"  
        elif input_image_bytes == self.IMG_BYTES_AIRBLADE:
            mock_response.text = "Xôi gấc" 
        elif input_image_bytes == self.IMG_BYTES_HIGH_RES:
            mock_response.text = "Bún giò heo" 
        elif input_image_bytes == self.IMG_BYTES_ERROR:
            # Trường hợp hình lỗi trả về undefined
            mock_response.text = "undefined"
        else:
            mock_response.text = "Món ăn không xác định"
            
        return mock_response

    @patch('FoodRecognition.genai.GenerativeModel')
    def test_food_recognition_cases(self, MockGenerativeModel):
        # Setup Mock cho Model
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.side_effect = self.mock_generate_content_side_effect

        # --- CASE 1: Ảnh bị mờ (static/images/testing/pho_blur.png) ---
        """
        Case 1: Ảnh bị mờ của món Phở Bò.
        Kỳ vọng: Trả về tên món ăn phù hợp nhất dựa vào đặc trưng bức hình.
        """
        file_blur = MagicMock()
        file_blur.read.return_value = self.IMG_BYTES_BLUR
        file_blur.mimetype = 'image/png'
        file_blur.filename = 'pho_blur.png'

        response_1 = FoodRecognition.replyToImage(file_blur)
        json_data_1 = response_1.get_json()

        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(json_data_1['food_name'], "Phở Bò")
        self.assertIn("The food you are looking for is Phở Bò", json_data_1['message'])


        # --- CASE 2: Ảnh xe máy (static/images/testing/airblade.png) ---
        """
        Case 2: Ảnh chiếc xe airblade đỏ.
        Kỳ vọng: Trả về tên món ăn phù hợp nhất dựa vào đặc trưng bức hình.
        """
        file_airblade = MagicMock()
        file_airblade.read.return_value = self.IMG_BYTES_AIRBLADE
        file_airblade.mimetype = 'image/png'
        file_airblade.filename = 'airblade.png'

        response_2 = FoodRecognition.replyToImage(file_airblade)
        json_data_2 = response_2.get_json()

        self.assertEqual(response_2.status_code, 200)
        self.assertEqual(json_data_2['food_name'], "Xôi gấc")


        # --- CASE 3: Ảnh độ phân giải cao (static/images/testing/pho_high_resolution.jpg) ---
        """
        Case 3: Ảnh độ phân giải cao của món Bún giò heo.
        Kỳ vọng: Trả về tên món ăn phù hợp nhất dựa vào đặc trưng bức hình.
        """
        file_high_res = MagicMock()
        file_high_res.read.return_value = self.IMG_BYTES_HIGH_RES
        file_high_res.mimetype = 'image/jpeg' 
        file_high_res.filename = 'pho_high_resolution.jpg'

        response_3 = FoodRecognition.replyToImage(file_high_res)
        json_data_3 = response_3.get_json()

        self.assertEqual(response_3.status_code, 200)
        self.assertEqual(json_data_3['food_name'], "Bún giò heo")

        # --- CASE 4: Ảnh bị lỗi (static/images/testing/error_picture.png) ---
        """
        Test các trường hợp nhận diện món ăn.
        Kỳ vọng: Trả về không định dạng được tên món ăn.
        """
        file_error = MagicMock()
        file_error.read.return_value = self.IMG_BYTES_ERROR
        file_error.mimetype = 'image/png'
        file_error.filename = 'error_picture.png'

        response_4 = FoodRecognition.replyToImage(file_error)
        json_data_4 = response_4.get_json()

        # Kiểm tra kết quả trả về là undefined
        self.assertEqual(response_4.status_code, 200)
        self.assertEqual(json_data_4['food_name'], "undefined")

if __name__ == '__main__':
    unittest.main()