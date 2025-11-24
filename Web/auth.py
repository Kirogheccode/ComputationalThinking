# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import add_user, get_user_by_username, get_user_by_email, save_otp, verify_otp_code
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

auth_bp = Blueprint('auth', __name__)

# --- CẤU HÌNH EMAIL (Thay đổi thông tin của bạn ở đây) ---
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = 'smarttourism24c11gr1@gmail.com' # Thay bằng email của bạn
SENDER_PASSWORD = 'lawisgcjshwfvley' # Thay bằng App Password của bạn

def send_email_otp(to_email, otp):
    """Hàm gửi email sử dụng thư viện chuẩn smtplib"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = "Mã xác thực đăng ký Smart Tourism"

        body = f"Chào bạn,\n\nMã xác thực (OTP) của bạn là: {otp}\nMã này sẽ hết hạn sau 5 phút.\n\nCảm ơn bạn!"
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Lỗi gửi mail: {e}")
        return False

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            flash('Vui lòng điền đầy đủ thông tin.', 'danger')
            return render_template('register.html')

        # 1. Kiểm tra User/Email đã tồn tại trong DB chưa
        if get_user_by_username(username):
            flash('Tên người dùng đã tồn tại.', 'danger')
            return render_template('register.html', username=username, email=email)
        
        if get_user_by_email(email):
            flash('Email này đã được đăng ký.', 'danger')
            return render_template('register.html', username=username, email=email)

        # 2. Tạo OTP và gửi mail
        otp = str(random.randint(100000, 999999))
        
        if send_email_otp(email, otp):
            # 3. Lưu OTP vào DB
            save_otp(email, otp)
            
            # 4. Lưu thông tin đăng ký tạm thời vào Session (chưa lưu vào DB Users)
            session['temp_register'] = {
                'username': username,
                'email': email,
                'password_hash': generate_password_hash(password)
            }
            
            flash(f'Mã OTP đã được gửi đến {email}. Vui lòng kiểm tra hộp thư.', 'info')
            return redirect(url_for('auth.verify_otp'))
        else:
            flash('Lỗi gửi email. Vui lòng kiểm tra lại email hoặc thử lại sau.', 'danger')
            return render_template('register.html', username=username, email=email)
    
    return render_template('register.html')

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    # Nếu không có thông tin đăng ký tạm, đá về register
    if 'temp_register' not in session:
        return redirect(url_for('auth.register'))

    email = session['temp_register']['email']

    if request.method == 'POST':
        otp_input = request.form['otp']
        
        # 5. Kiểm tra OTP
        if verify_otp_code(email, otp_input):
            # OTP đúng -> Tạo user thật vào DB
            user_data = session['temp_register']
            if add_user(user_data['username'], user_data['email'], user_data['password_hash']):
                # Xóa session tạm
                session.pop('temp_register', None)
                flash('Đăng ký và xác thực thành công! Vui lòng đăng nhập.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Có lỗi xảy ra khi tạo tài khoản.', 'danger')
        else:
            flash('Mã OTP không đúng hoặc đã hết hạn.', 'danger')

    return render_template('verify_otp.html', email=email)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)

        if user and check_password_hash(user['password'], password):
            # Kiểm tra trạng thái verified (mặc dù code trên auto verified=1, nhưng giữ logic này để an toàn)
            if user['verified'] == 1:
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Đăng nhập thành công!', 'success')
                return redirect(url_for('your_account'))
            else:
                flash('Tài khoản chưa được xác thực.', 'warning')
        else:
            flash('Tên người dùng hoặc mật khẩu không đúng.', 'danger')
            return render_template('login.html', username=username)
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/resend-otp')
def resend_otp():
    if 'temp_register' not in session:
        return redirect(url_for('auth.register'))
    
    email = session['temp_register']['email']
    otp = str(random.randint(100000, 999999))
    
    if send_email_otp(email, otp):
        save_otp(email, otp)
        flash('Đã gửi lại mã OTP mới.', 'info')
    else:
        flash('Không thể gửi mail.', 'danger')
        
    return redirect(url_for('auth.verify_otp'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để truy cập trang này.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function