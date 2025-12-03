# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import add_user, get_user_by_username, get_user_by_email, save_otp, verify_otp_code
import random
import smtplib
import os
from extensions import oauth
from dotenv import load_dotenv
from database import get_or_create_oauth_user
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

auth_bp = Blueprint('auth', __name__)

# --- CẤU HÌNH EMAIL ---
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

if not SENDER_EMAIL:
    print("Error: SENDER_EMAIL not found. Please check your .env file.")
    exit()

if not SENDER_PASSWORD:
    print("Error: SENDER_PASSWORD not found. Please check your .env file.")
    exit()
# -------------------------------------------------------

# --- CẤU HÌNH FACEBOOK VÀ GOOGLE ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")

if not GOOGLE_CLIENT_ID:
    print("Error: GOOGLE_CLIENT_ID not found. Please check your .env file.")
    exit()

if not GOOGLE_CLIENT_SECRET:
    print("Error: GOOGLE_CLIENT_SECRET not found. Please check your .env file.")
    exit()

if not FACEBOOK_CLIENT_ID:
    print("Error: FACEBOOK_CLIENT_ID not found. Please check your .env file.")
    exit()

if not FACEBOOK_CLIENT_SECRET:
    print("Error: FACEBOOK_CLIENT_SECRET not found. Please check your .env file.")
    exit()
# -------------------------------------------------------

auth_bp = Blueprint('auth', __name__)

# --- CẤU HÌNH OAUTH ---
# Đăng ký Google
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Đăng ký Facebook
oauth.register(
    name='facebook',
    client_id=os.getenv("FACEBOOK_CLIENT_ID"),
    client_secret=os.getenv("FACEBOOK_CLIENT_SECRET"),
    api_base_url='https://graph.facebook.com/v19.0/',
    access_token_url='https://graph.facebook.com/v19.0/oauth/access_token',
    authorize_url='https://www.facebook.com/v19.0/dialog/oauth',
    client_kwargs={'scope': 'email public_profile'}
)

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

# --- ROUTE CHO GOOGLE ---
@auth_bp.route('/login/google')
def login_google():
    redirect_uri = url_for('auth.google_auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/login/google/callback')
def google_auth():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info: # Fallback nếu userinfo không có trong token
             user_info = oauth.google.userinfo()
             
        email = user_info.get('email')
        name = user_info.get('name') or user_info.get('given_name') or "GoogleUser"

        # Lưu vào DB
        user = get_or_create_oauth_user(name, email)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Đăng nhập bằng Google thành công!', 'success')
            return redirect(url_for('your_account'))
        else:
            flash('Lỗi khi tạo tài khoản Google.', 'danger')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        print(f"Google Login Error: {e}")
        flash('Đăng nhập Google thất bại.', 'danger')
        return redirect(url_for('auth.login'))

# --- ROUTE CHO FACEBOOK ---
@auth_bp.route('/login/facebook')
def login_facebook():
    redirect_uri = url_for('auth.facebook_auth', _external=True)
    return oauth.facebook.authorize_redirect(redirect_uri)

@auth_bp.route('/login/facebook/callback')
def facebook_auth():
    try:
        token = oauth.facebook.authorize_access_token()
        resp = oauth.facebook.get('me?fields=id,name,email')
        profile = resp.json()
        
        email = profile.get('email')
        name = profile.get('name') or "FacebookUser"

        if not email:
            flash('Tài khoản Facebook của bạn không công khai Email. Vui lòng đăng ký thủ công.', 'warning')
            return redirect(url_for('auth.register'))

        # Lưu vào DB
        user = get_or_create_oauth_user(name, email)

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Đăng nhập bằng Facebook thành công!', 'success')
            return redirect(url_for('your_account'))
        else:
            flash('Lỗi khi tạo tài khoản Facebook.', 'danger')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        print(f"Facebook Login Error: {e}")
        flash('Đăng nhập Facebook thất bại.', 'danger')
        return redirect(url_for('auth.login'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để truy cập trang này.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function