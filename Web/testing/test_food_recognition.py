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

        # Giả lập dữ liệu bytes cho 3 bức ảnh (để phân biệt chúng khi mock)
        # Vì unit test không nên phụ thuộc vào file thực tế trên ổ cứng
        self.IMG_BYTES_BLUR = b"binary_data_of_pho_blur"
        self.IMG_BYTES_AIRBLADE = b"binary_data_of_airblade"
        self.IMG_BYTES_HIGH_RES = b"binary_data_of_pho_high_res"

    def tearDown(self):
        self.ctx.pop()

    # Hàm giả lập (Side Effect) cho model.generate_content
    # Hàm này sẽ kiểm tra xem đầu vào là ảnh nào để trả về tên món ăn tương ứng
    def mock_generate_content_side_effect(self, contents):
        # contents là list [prompt, image_dict] được truyền vào từ FoodRecognition.py
        # image_dict có dạng {"mime_type": ..., "data": ...}
        
        input_image_bytes = contents[1]['data']
        
        # Tạo đối tượng response giả
        mock_response = MagicMock()

        if input_image_bytes == self.IMG_BYTES_BLUR:
            mock_response.text = "Phở Bò"  
        elif input_image_bytes == self.IMG_BYTES_AIRBLADE:
            mock_response.text = "Xôi gấc" 
        elif input_image_bytes == self.IMG_BYTES_HIGH_RES:
            mock_response.text = "Bún giò heo" 
        else:
            mock_response.text = "Món ăn không xác định"
            
        return mock_response

    @patch('FoodRecognition.genai.GenerativeModel')
    def test_food_recognition_cases(self, MockGenerativeModel):
        """
        Test 3 trường hợp nhận diện món ăn.
        """
        # 1. Setup Mock cho Model
        mock_model_instance = MockGenerativeModel.return_value
        # Gán hàm side_effect của mình vào mock
        mock_model_instance.generate_content.side_effect = self.mock_generate_content_side_effect

        # --- CASE 1: Ảnh bị mờ (static/images/testing/pho_blur.png) ---
        # Giả lập file upload
        file_blur = MagicMock()
        file_blur.read.return_value = self.IMG_BYTES_BLUR
        file_blur.mimetype = 'image/png'
        file_blur.filename = 'pho_blur.png'

        # Gọi hàm
        response_1 = FoodRecognition.replyToImage(file_blur)
        json_data_1 = response_1.get_json()

        # Kiểm tra kết quả
        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(json_data_1['food_name'], "Phở Bò")
        self.assertIn("The food you are looking for is Phở Bò", json_data_1['message'])


        # --- CASE 2: Ảnh xe máy (static/images/testing/airblade.png) ---
        # Giả lập file upload
        file_airblade = MagicMock()
        file_airblade.read.return_value = self.IMG_BYTES_AIRBLADE
        file_airblade.mimetype = 'image/png'
        file_airblade.filename = 'airblade.png'

        # Gọi hàm
        response_2 = FoodRecognition.replyToImage(file_airblade)
        json_data_2 = response_2.get_json()

        # Kiểm tra kết quả (Nếu không là đồ ăn thì nhận diện đặc trưng để đưa ra tên món ăn gần nhất với bức hình)
        self.assertEqual(response_2.status_code, 200)
        self.assertEqual(json_data_2['food_name'], "Xôi gấc")


        # --- CASE 3: Ảnh độ phân giải cao (static/images/testing/pho_high_resolution.jpg) ---
        # Giả lập file upload
        file_high_res = MagicMock()
        file_high_res.read.return_value = self.IMG_BYTES_HIGH_RES
        file_high_res.mimetype = 'image/jpeg' # jpg
        file_high_res.filename = 'pho_high_resolution.jpg'

        # Gọi hàm
        response_3 = FoodRecognition.replyToImage(file_high_res)
        json_data_3 = response_3.get_json()

        # Kiểm tra kết quả
        self.assertEqual(response_3.status_code, 200)
        self.assertEqual(json_data_3['food_name'], "Bún giò heo")

if __name__ == '__main__':
    unittest.main()