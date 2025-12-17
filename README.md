# 📘 WEBSITE SETUP & RUNNING GUIDE (FLASK)

This document provides step-by-step instructions for **lecturers** to install and run the Flask-based website on a local machine using VS Code.

---

## 1️⃣ System Requirements

This website is built using **Flask (Python Web Framework)**.

Please make sure the system has:

- **Python** ≥ 3.12   
- **pip** (Python package manager)  
- **Git** (recommended, optional)

Check versions using:
```bash
python --version
pip --version
```

---

## 2️⃣ Project Directory Structure
```
Web/
├── data/                # Database
├── static/              # Static files (CSS, JS, images)
│   └── images/          # 📂 Large image folder
├── templates/           # HTML templates (Jinja2)
├── testing/             # Unit test
├── app.py/              # Main entry file 
├── auth.py/             # Login/Register
├── Currency.py/         # Currency Converter
├── database.py/         # Handling all SQLite operations
├── extensions.py/       # Initialize OAuth support
├── FoodLoading.py/      # Load food data to render
├── FoodRecognition.py/  # Food recognition
├── lang.py/             # Language support (EN/VI)
├── requirements.txt/    # Important libraries
├── Routing.py/          # Draw route and map
├── SaveAnswer.py/       # Save user answer for chatbot
└── Search_Clone_2.py/   # Chatbot 
```

📌 **Note:** The `images/` folder is relatively large, so copying or extracting the project may take additional time.

---

## 3️⃣ Create & Activate a Virtual Environment (Recommended)

### ▶️ On Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### ▶️ On macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

Once activated, `(venv)` will appear at the beginning of the terminal line.

---

## 4️⃣ Install Required Dependencies

All required libraries are listed in **`requirements.txt`**.

Run:
```bash
pip install -r requirements.txt
```

⏳ This process may take a few minutes depending on internet speed.

---

## 5️⃣ Configure Environment Variables (`.env`)

A pre-configured **`.env` file is already included in the submitted ZIP file**.

### ✅ Steps for the lecturer:
1. Download and extract the project ZIP file.
2. Locate the provided **`.env`** file inside the ZIP package.
3. Copy or move the **`.env`** file into the **Web (project root) directory**.

📌 **Important:**
- Please ensure the `.env` file is placed at the **same level as `app.py` / `requirements.txt`**.
- No additional configuration is required.
- The `.env` file already contains all necessary environment variables

---
## 6️⃣ Download & Configure `foody_images` Folder

A large image folder named **`foody_images`** is included in the submitted ZIP file.

### ✅ Steps for the lecturer:
1. Download and extract the project ZIP file.
2. Locate the **`foody_images/`** folder inside the ZIP package.
3. Copy the entire **`foody_images/`** folder into the following directory:

```text
Web/static/
```

📌 **Important:**
- Please make sure the folder name remains **exactly `foody_images`**.
- Do not rename or modify the folder structure.
- This folder contains image assets required for food display features.

---

## 7️⃣ Run the Flask Application

### ▶️ Method 1: Run directly
```bash
python app.py
```

### ▶️ Method 2: Using Flask CLI
```bash
flask run
```

If successful, the terminal will display:
```text
Running on http://127.0.0.1:5000/
```

➡️ Open a browser and visit: **http://127.0.0.1:5000/**

---

## 8️⃣ Common Issues & Troubleshooting

### ❌ Error: `ModuleNotFoundError`
➡️ Dependencies are missing. Run:
```bash
pip install -r requirements.txt
```

### ❌ Images not loading
➡️ Check that: The `static/images/` folder exists

### ❌ `.env` variables not working
➡️ Make sure the following package is installed:
```bash
pip install python-dotenv
```

# 🧪 UNIT TEST RUNNING GUIDE

This document explains the **unit test directory structure** and **how to run unit test files using Python**.

---

## 1️⃣ Unit Test Directory Structure

All unit test files are located inside the `testing` folder with the following structure:

```text
testing/
├── test_chatbot.py
├── test_currency.py
├── test_favorite.py
├── test_food_recognition.py
├── test_register.py
└── test_routing.py
```
Notes:
- The testing/ folder contains all unit test files
- Each test_*.py is responsible for testing a specific module
## 2️⃣ How to Run Unit Tests
Open terminal/Command Prompt at the Web directory and execute:
```bash
python .\testing\file_name.py
```
Example:
```bash
python .testing\test_chatbot.py
```
# 🧪 Unit Test Coverage Summary – Search_Clone_2

This unit test suite covers the following main areas of the `Search_Clone_2` module:

- **Environment setup**
  - API key initialization
  - Safe module importing with mocked dependencies

- **Helper functions**
  - Distance calculation (`haversine`)
  - Geographic bounding box calculation
  - Opening-hour validation logic

- **External API wrappers**
  - Location coordinates retrieval (Geoapify)
  - Nutrition information lookup (Spoonacular)

- **AI-based intent routing**
  - User intent classification
  - Culture-related question handling

- **Core application logic**
  - Restaurant recommendation workflow
  - Daily menu planning logic

- **Main integration flow**
  - User request handling via `replyToUser`
  - Correct handler dispatch based on detected task
  - Safe persistence calls with mocked database saver

All external services, databases, and AI models are fully mocked to ensure isolated, reliable, and repeatable unit tests.
# 🧪 Unit Test Coverage Summary – Currency Module

The unit tests for the `Currency` module cover the following key areas:

- **Environment initialization**
  - API keys are loaded correctly from environment variables
  - Module imports safely with test configuration

- **Exchange rate API handling**
  - Successful exchange rate retrieval
  - API error responses (e.g. invalid key)
  - Network or unexpected exceptions

- **Currency conversion logic**
  - Foreign currency → VND conversion
  - VND → foreign currency conversion
  - Proper handling when exchange rate retrieval fails

- **AI-based money recognition (Gemini Vision)**
  - Successful recognition of a single banknote
  - Rejection when multiple items are detected
  - Graceful handling of Gemini API exceptions

All external services (exchange rate API and Gemini AI) are fully mocked to ensure isolated, stable, and repeatable unit tests.
# 🧪 Unit Test Coverage Summary – Favorite Feature

The unit tests cover the following aspects of the **Favorite** functionality:

- **Application initialization**
  - Flask app loaded successfully with all dependent modules mocked
  - Authentication decorator (`login_required`) safely bypassed for testing

- **User session handling**
  - Simulated logged-in user via Flask session
  - Handling of unauthenticated requests

- **Favorite management**
  - Adding a place to favorites when the user is logged in
  - Correct interaction with the database layer (`add_favorite`)
  - Proper JSON response on successful favorite addition

- **Access control**
  - Rejecting favorite actions when the user is not logged in (401 Unauthorized)

- **External dependency isolation**
  - Database operations fully mocked
  - Routing, Currency, FoodRecognition, and other modules mocked

These tests ensure the favorite feature behaves correctly for both authenticated and unauthenticated users without relying on real databases or authentication services.

# 🧪 Unit Test Coverage Summary – FoodRecognition Module

The unit tests for the `FoodRecognition` module cover the following aspects:

- **Flask application context**
  - Proper handling of requests within an active Flask app context

- **AI-based food image recognition**
  - Recognition from blurred food images
  - Recognition from high-resolution food images
  - Handling of non-food images
  - Handling of corrupted or unreadable images

- **Response validation**
  - Correct HTTP status codes
  - Correct JSON response structure
  - Proper extraction of recognized food names

- **External dependency isolation**
  - Gemini AI model fully mocked
  - No real image uploads or external API calls

These tests ensure that the image-to-food recognition pipeline behaves correctly across common and edge-case scenarios.
# 🧪 Unit Test Coverage Summary – User Registration (Auth Module)

The unit tests cover the following registration-related scenarios:

- **Application setup**
  - Flask app initialization with mocked environment variables
  - Safe app startup with all external modules mocked

- **Input validation**
  - Empty registration fields
  - Weak password detection
  - Duplicate username detection

- **Registration edge cases**
  - Preventing registration when username already exists
  - Ensuring OTP email is NOT sent if validation fails

- **Successful registration flow**
  - New user registration with valid data
  - OTP generation and email sending
  - Redirect to OTP confirmation step

- **External dependency isolation**
  - Database access mocked
  - Email sending mocked
  - Password strength checking mocked

These tests ensure the registration flow handles both error cases and successful scenarios correctly without relying on real databases or email services.
# 🧪 Unit Test Coverage Summary – Routing Module (Edge Cases)

The unit tests cover the following routing-related scenarios:

- **Flask context handling**
  - Proper execution within an active Flask application context

- **Input validation**
  - Origin address provided as a number
  - Destination provided as an invalid or weird string

- **Address resolution logic**
  - Same origin and destination handling
  - Ambiguous destination address resolution
  - Non-existent destination address handling

- **Routing behavior**
  - Normal routing flow with valid coordinates
  - Handling of impossible routes (e.g. Vietnam → Italy)
  - Proper error responses when routing service fails

- **External dependency isolation**
  - Geocoding mocked
  - Database coordinate lookup mocked
  - Routing service (ORS) mocked

These tests ensure the routing logic behaves correctly across common edge cases and failure scenarios without relying on real map services.