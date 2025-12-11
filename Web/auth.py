# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import add_user, get_user_by_username, get_user_by_email, save_otp, verify_otp_code
import random
import smtplib
import os
import uuid
import re
from extensions import oauth
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

load_dotenv()

auth_bp = Blueprint('auth', __name__)

# --- DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để truy cập trang này.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# --- CẤU HÌNH EMAIL ---
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# --- CẤU HÌNH OAUTH ---
# Đảm bảo biến môi trường tồn tại
if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
    print("Warning: Google OAuth credentials missing.")

if not os.getenv("FACEBOOK_CLIENT_ID") or not os.getenv("FACEBOOK_CLIENT_SECRET"):
    print("Warning: Facebook OAuth credentials missing.")

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
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("Chưa cấu hình Email gửi OTP.")
        return False
        
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

# Kiểm tra mật khẩu mạnh

def is_strong_password(password):
    # ít nhất 8 ký tự
    if len(password) < 8:
        return False
    
    # có chữ in hoa
    if not re.search(r"[A-Z]", password):
        return False

    # có chữ thường
    if not re.search(r"[a-z]", password):
        return False

    # có số
    if not re.search(r"[0-9]", password):
        return False

    # có ký tự đặc biệt
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False

    return True

# --- ROUTES ---

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            flash('Vui lòng điền đầy đủ thông tin.', 'danger')
            return render_template('register.html')

        if not is_strong_password(password):
            flash('Mật khẩu phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.', 'danger')
            return render_template('register.html', username=username, email=email)

        
        if get_user_by_username(username):
            flash('Tên người dùng đã tồn tại.', 'danger')
            return render_template('register.html', username=username, email=email)

        otp = str(random.randint(100000, 999999))
        
        if send_email_otp(email, otp):
            save_otp(email, otp)
            session['temp_register'] = {
                'username': username,
                'email': email,
                'password_hash': generate_password_hash(password)
            }
            flash(f'Mã OTP đã được gửi đến {email}.', 'info')
            return redirect(url_for('auth.verify_otp'))
        else:
            flash('Lỗi gửi email. Vui lòng thử lại sau.', 'danger')
    
    return render_template('register.html')

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'temp_register' not in session:
        return redirect(url_for('auth.register'))

    email = session['temp_register']['email']

    if request.method == 'POST':
        otp_input = request.form['otp']
        if verify_otp_code(email, otp_input):
            user_data = session['temp_register']
            if add_user(user_data['username'], user_data['email'], user_data['password_hash']):
                session.pop('temp_register', None)
                flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
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
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            # Redirect về trang trước đó nếu có
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
                
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('index')) # Hoặc 'account_page'
        else:
            flash('Tên người dùng hoặc mật khẩu không đúng.', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear() # Xóa sạch session an toàn hơn
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

@auth_bp.route('/complete-oauth', methods=['GET', 'POST'])
def complete_oauth():
    if 'oauth_temp_data' not in session:
        return redirect(url_for('auth.login'))

    oauth_data = session['oauth_temp_data']
    email = oauth_data['email']
    provider = oauth_data.get('provider', 'Social')

    if request.method == 'POST':
        username = request.form['username'].strip()
        if get_user_by_username(username):
            flash(f'Tên đăng nhập "{username}" đã tồn tại.', 'danger')
        else:
            dummy_password = str(uuid.uuid4())
            password_hash = generate_password_hash(dummy_password)

            if add_user(username, email, password_hash):
                user = get_user_by_username(username)
                session['user_id'] = user['id']
                session['username'] = user['username']
                session.pop('oauth_temp_data', None)
                
                flash(f'Chào mừng {username}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Lỗi database.', 'danger')

    return render_template('complete_oauth.html', email=email, provider=provider)

@auth_bp.route('/login/google')
def login_google():
    redirect_uri = url_for('auth.google_auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/login/google/callback')
def google_auth():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo') or oauth.google.userinfo()
        email = user_info.get('email')
        name = user_info.get('name')

        user = get_user_by_email(email)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            session['oauth_temp_data'] = {'email': email, 'name': name, 'provider': 'Google'}
            return redirect(url_for('auth.complete_oauth'))
    except Exception as e:
        print(f"Google Auth Error: {e}")
        flash("Lỗi đăng nhập Google.", "danger")
        return redirect(url_for('auth.login'))

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
        name = profile.get('name')

        if not email:
            flash('Facebook không cung cấp Email.', 'warning')
            return redirect(url_for('auth.register'))

        user = get_user_by_email(email)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            session['oauth_temp_data'] = {'email': email, 'name': name, 'provider': 'Facebook'}
            return redirect(url_for('auth.complete_oauth'))
    except Exception as e:
        print(f"Facebook Auth Error: {e}")
        flash("Lỗi đăng nhập Facebook.", "danger")
        return redirect(url_for('auth.login'))