# BÁO CÁO DỰ ÁN: HỆ THỐNG DU LỊCH THÔNG MINH (SMART TOURISM SYSTEM)

## 1. Giới thiệu công cụ và Công nghệ sử dụng

Dự án được xây dựng theo mô hình ứng dụng web (Web Application) với kiến trúc **Client-Server**, sử dụng ngôn ngữ lập trình Python làm nòng cốt. Các công cụ cụ thể bao gồm:

### a. Backend (Phía máy chủ)
*   **Ngôn ngữ:** Python.
*   **Framework:** **Flask**. Đây là một micro-framework nhẹ, linh hoạt, giúp xây dựng web server nhanh chóng, hỗ trợ tốt việc định tuyến (routing) và xử lý request/response.
*   **Thư viện hỗ trợ:**
    *   `Werkzeug.security`: Dùng để mã hóa mật khẩu (hashing) đảm bảo an toàn thông tin.
    *   `smtplib`: Thư viện chuẩn của Python dùng để gửi email xác thực (OTP) qua giao thức SMTP.
    *   `sqlite3`: Thư viện tích hợp sẵn để tương tác với cơ sở dữ liệu.

### b. Frontend (Giao diện người dùng)
*   **HTML5/CSS3:** Xây dựng cấu trúc và định dạng giao diện. Sử dụng **Jinja2 Templating** (tích hợp trong Flask) để hiển thị dữ liệu động từ server ra HTML.
*   **Bootstrap 5:** Framework CSS giúp giao diện responsive (tương thích di động) và thẩm mỹ.
*   **JavaScript (ES6):** Xử lý các tương tác phía client như gọi API chatbot, vẽ bản đồ.
*   **Thư viện bên thứ 3:**
    *   **Leaflet.js:** Hiển thị bản đồ tương tác và vẽ đường đi.
    *   **AOS (Animate On Scroll):** Tạo hiệu ứng chuyển động khi cuộn trang.

### c. Cơ sở dữ liệu
*   **SQLite:** Hệ quản trị cơ sở dữ liệu quan hệ dạng file (Serverless).
    *   *Lý do chọn:* Không cần cài đặt server riêng, dữ liệu lưu trong 1 file duy nhất (`smart_tourism.db`), dễ dàng sao chép và triển khai cho các dự án vừa và nhỏ.

---

## 2. Cơ chế tương tác giữa Frontend (FE) và Backend (BE)

Hệ thống sử dụng hai cơ chế tương tác chính:

### a. Server-Side Rendering (SSR)
*   **Quy trình:** Khi người dùng truy cập các trang như Trang chủ, Đăng nhập, Đăng ký, Tài khoản.
*   **Hoạt động:**
    1.  Trình duyệt gửi Request (GET) tới Server.
    2.  Flask nhận request, truy vấn dữ liệu từ Database (nếu cần).
    3.  Flask chèn dữ liệu vào các khuôn mẫu HTML (Template) thông qua **Jinja2**.
    4.  Server trả về toàn bộ mã HTML đã hoàn chỉnh cho trình duyệt hiển thị.

### b. Client-Side Rendering & API (AJAX/Fetch)
*   **Quy trình:** Sử dụng cho các tính năng cần phản hồi tức thì mà không tải lại trang (Chatbot, Tìm đường, Bản đồ).
*   **Hoạt động:**
    1.  JavaScript tại FE thu thập dữ liệu (ví dụ: tin nhắn chat) và gửi Request (POST) dạng JSON tới các API endpoint (ví dụ: `/api/chat`).
    2.  Backend xử lý logic (gọi module tìm kiếm, tính toán đường đi) và trả về kết quả dạng **JSON**.
    3.  JavaScript nhận JSON và cập nhật lại một phần giao diện (DOM) mà không cần F5 lại trang.

---

## 3. Cơ sở dữ liệu và Cách thức lưu trữ

Cơ sở dữ liệu SQLite được thiết kế với mô hình quan hệ (Relational), bao gồm các bảng chính sau:

### a. Cấu trúc bảng

1.  **Bảng `users` (Người dùng):**
    *   Lưu trữ thông tin tài khoản.
    *   **Cột:** `id` (Khóa chính), `username`, `email`, `password` (Lưu dạng mã hóa Hash, không lưu text thường), `verified` (Trạng thái xác thực: 0 hoặc 1).
2.  **Bảng `email_otp` (Mã xác thực tạm thời):**
    *   Dùng để lưu mã OTP trong quá trình đăng ký.
    *   **Cột:** `id`, `email`, `otp_code`, `expired_at` (Thời gian hết hạn).
    *   **Cơ chế:** Khi người dùng yêu cầu đăng ký, hệ thống tạo OTP lưu vào đây. Khi xác thực xong hoặc hết hạn, OTP sẽ bị xóa để bảo mật.
3.  **Bảng `food_posts` (Bài đăng ẩm thực):**
    *   Lưu các bài review món ăn của người dùng.
    *   **Cột:** `id`, `user_id` (Khóa ngoại liên kết với bảng users), `food_name`, `description`, `image_filename`, `posted_at`.

### b. Cách hoạt động
*   Sử dụng module `database.py` để quản lý kết nối.
*   Mỗi khi có yêu cầu (ví dụ: Đăng nhập), Flask sẽ mở kết nối `conn = get_db_connection()`, thực thi câu lệnh SQL (SELECT/INSERT), nhận kết quả và đóng kết nối ngay lập tức để tiết kiệm tài nguyên.

---

## 4. Các chức năng chính của hệ thống

### a. Hệ thống xác thực bảo mật (Authentication)
*   **Đăng ký 2 lớp (2FA):**
    *   Người dùng nhập thông tin -> Hệ thống kiểm tra trùng lặp.
    *   Backend sinh mã OTP ngẫu nhiên và gửi qua Email (sử dụng Gmail SMTP).
    *   Thông tin người dùng được lưu tạm trong **Session**, OTP lưu trong **DB**.
    *   Chỉ khi người dùng nhập đúng OTP, tài khoản mới chính thức được ghi vào bảng `users`.
*   **Đăng nhập:** Kiểm tra Username và so khớp mật khẩu đã mã hóa (Hash Check). Sử dụng `session` của Flask để lưu trạng thái đăng nhập.
*   **Middleware:** Sử dụng decorator `@login_required` để chặn truy cập trái phép vào các trang cá nhân.

### b. Chatbot tư vấn ẩm thực
*   Người dùng nhập câu hỏi (ví dụ: "Ăn gì ở quận 1?").
*   Frontend gửi tin nhắn đến `/api/chat`.
*   Backend (Module `SearchModule`) phân tích từ khóa và tìm kiếm trong dữ liệu nhà hàng.
*   Kết quả trả về danh sách món ăn, địa chỉ, giờ mở cửa.

### c. Bản đồ và Tìm đường (Map & Routing)
*   Tích hợp bản đồ Leaflet.
*   Chức năng **Geocoding**: Chuyển đổi địa chỉ nhập vào (text) thành tọa độ (kinh độ, vĩ độ).
*   Chức năng **Routing**: Tính toán đường đi từ vị trí người dùng đến quán ăn và vẽ lộ trình lên bản đồ.

### d. Quản lý bài đăng cá nhân (User Account)
*   Người dùng đã đăng nhập có thể viết bài review món ăn.
*   Hỗ trợ tải lên hình ảnh (Image Upload):
    *   Ảnh được kiểm tra định dạng (.jpg, .png).
    *   Tên file được chuẩn hóa (`secure_filename`) để tránh lỗi hệ thống file.
    *   Đường dẫn ảnh lưu vào DB, file ảnh lưu trong thư mục `static/images`.
*   Hiển thị danh sách bài đăng theo thứ tự thời gian mới nhất.

---

## 5. Kết luận
Hệ thống Smart Tourism System là một giải pháp web trọn vẹn kết hợp giữa việc quản lý dữ liệu truyền thống (SQL) và các tính năng tương tác hiện đại (Map, Chatbot). Việc áp dụng quy trình xác thực qua Email giúp tăng cường tính bảo mật và độ tin cậy cho tài khoản người dùng. Cấu trúc code được chia module rõ ràng (Auth, Database, Routing) giúp dễ dàng bảo trì và mở rộng trong tương lai.