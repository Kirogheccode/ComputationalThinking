import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# --- 1. SETUP ENVIRONMENT ---
# Thiết lập biến môi trường giả để app không bị lỗi khi khởi động
os.environ["SECRET_KEY"] = "TEST_SECRET_KEY"
os.environ["SENDER_EMAIL"] = "test@example.com"
os.environ["SENDER_PASSWORD"] = "test_password"
# Các biến OAuth giả để tránh cảnh báo
os.environ["GOOGLE_CLIENT_ID"] = "dummy"
os.environ["GOOGLE_CLIENT_SECRET"] = "dummy"
os.environ["GITHUB_CLIENT_ID"] = "dummy"
os.environ["GITHUB_CLIENT_SECRET"] = "dummy"

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

sys.modules["extensions"] = MagicMock()
sys.modules["database"] = MagicMock()
sys.modules["Routing"] = MagicMock()
sys.modules["Currency"] = MagicMock()
sys.modules["FoodRecognition"] = MagicMock()
sys.modules["FoodLoading"] = MagicMock()
sys.modules["Search_Clone_2"] = MagicMock()
sys.modules["SaveAnswer"] = MagicMock()
sys.modules["lang"] = MagicMock()

mock_lang = MagicMock()
mock_lang.translations = {"vi": {}, "en": {}}
sys.modules["lang"] = mock_lang

# --- IMPORT MODULE UNDER TEST ---
try:
    # Thử import từ thư mục cha (nếu file test nằm trong folder testing)
    sys.path.append(os.path.join(current_dir, '..'))
    from app import app
except ImportError:
    # Fallback nếu cấu trúc thư mục khác
    import app

class TestAuthRegister(unittest.TestCase):

    # =========================================================================
    # A. SETUP & TEARDOWN
    # =========================================================================
    
    def setUp(self):
        """Thiết lập client test flask."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False # Tắt CSRF để test form dễ dàng
        app.config['SECRET_KEY'] = 'test_key'
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    # =========================================================================
    # B. EDGE CASE TESTS (Duplicate Username)
    # =========================================================================

    @patch('auth.get_user_by_username') # Mock hàm check DB trong auth.py
    @patch('auth.is_strong_password')   # Mock hàm check pass để bỏ qua logic phức tạp
    def test_register_duplicate_username(self, mock_is_strong, mock_get_user):
        """
        Test edge case: Đăng ký tài khoản với tên người dùng đã tồn tại.
        """
        # 1. Setup Mock behavior
        # Giả lập password luôn mạnh (để code không dừng ở bước check pass)
        mock_is_strong.return_value = True
        
        # Giả lập DB trả về user đã tồn tại (không phải None)
        mock_get_user.return_value = {
            'id': 123, 
            'username': 'existing_user', 
            'email': 'old@example.com'
        }

        # 2. Prepare Data
        form_data = {
            'username': 'existing_user',
            'email': 'new_email@example.com',
            'password': 'AnyPassword123!'
        }

        # 3. Action: Gửi POST request
        response = self.client.post('/register', data=form_data, follow_redirects=True)
        response_text = response.data.decode('utf-8')

        # 4. Assertions (Kiểm tra kết quả)
        
        # Kiểm tra hàm check DB đã được gọi với đúng username
        mock_get_user.assert_called_once_with('existing_user')
        
        # Kiểm tra thông báo lỗi xuất hiện trong HTML trả về
        self.assertIn('Tên người dùng đã tồn tại', response_text)
        
        # Kiểm tra status code (200 OK vì render lại trang register, không phải 500 lỗi server)
        self.assertEqual(response.status_code, 200)

    @patch('auth.get_user_by_username')
    @patch('auth.is_strong_password')
    @patch('auth.send_email_otp') # Mock thêm hàm gửi mail để đảm bảo nó KHÔNG được gọi
    def test_register_flow_stops_on_duplicate(self, mock_send_email, mock_is_strong, mock_get_user):
        """
        Test đảm bảo rằng nếu trùng tên, hệ thống KHÔNG gửi OTP.
        """
        # Setup
        mock_is_strong.return_value = True
        mock_get_user.return_value = {'username': 'duplicate'} # User tồn tại

        # Action
        self.client.post('/register', data={
            'username': 'duplicate',
            'email': 'test@test.com',
            'password': 'Pass'
        })

        # Assert
        # Hàm gửi email tuyệt đối không được chạy nếu trùng tên
        mock_send_email.assert_not_called()

    # --- MẬT KHẨU YẾU ---
    @patch('auth.is_strong_password') 
    def test_register_weak_password(self, mock_is_strong):
        """Test khi người dùng nhập mật khẩu yếu."""
        # Giả lập hàm check pass trả về False (Mật khẩu yếu)
        mock_is_strong.return_value = False
        
        response = self.client.post('/register', data={
            'username': 'user123',
            'email': 'user@test.com',
            'password': '123' # Pass yếu
        }, follow_redirects=True)
        
        response_text = response.data.decode('utf-8')
        
        # Kiểm tra xem có hiện thông báo lỗi mật khẩu không
        self.assertIn('Mật khẩu phải có ít nhất 8 ký tự', response_text)
        self.assertEqual(response.status_code, 200)

    # --- BỎ TRỐNG THÔNG TIN ---
    def test_register_empty_fields(self):
        """Test khi người dùng gửi form trống."""
        response = self.client.post('/register', data={
            'username': '', # Rỗng
            'email': '',
            'password': ''
        }, follow_redirects=True)
        
        response_text = response.data.decode('utf-8')
        self.assertIn('Vui lòng điền đầy đủ thông tin', response_text)

    @patch('auth.get_user_by_username')
    @patch('auth.is_strong_password')
    @patch('auth.send_email_otp')
    @patch('auth.save_otp') # Mock thêm hàm lưu OTP
    def test_register_success(self, mock_save_otp, mock_send_email, mock_is_strong, mock_get_user):
        """Test trường hợp mọi thứ đều đúng -> Chuyển sang trang nhập OTP."""
        
        # Setup: User chưa tồn tại (None), Pass mạnh (True), Gửi mail thành công (True)
        mock_get_user.return_value = None 
        mock_is_strong.return_value = True
        mock_send_email.return_value = True 

        response = self.client.post('/register', data={
            'username': 'new_user',
            'email': 'new@test.com',
            'password': 'StrongPass1!'
        }, follow_redirects=True) # follow_redirects=True để đi theo lệnh redirect
        
        response_text = response.data.decode('utf-8')

        mock_send_email.assert_called_once()
        self.assertIn('Mã OTP đã được gửi', response_text)

if __name__ == '__main__':
    unittest.main()