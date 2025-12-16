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
|── data/                # Database
|── static/              # Static files (CSS, JS, images)
│   └── images/          # 📂 Large image folder
│── templates/           # HTML templates (Jinja2)
│── testing/             # Unit test
│── app.py/              # Main entry file 
│── auth.py/             # Login/Register
│── Currency.py/         # Currency Converter
│── database.py/         # Handling all SQLite operations
│── extensions.py/       # Initialize OAuth support
│── FoodLoading.py/      # Load food data to render
│── FoodRecognition.py/  # Food recognition
│── lang.py/             # Language support (EN/VI)
│── requirements.txt/    # Important libraries
│── Routing.py/          # Draw route and map
│── SaveAnswer.py/       # Save user answer for chatbot
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
 

# 🧪 Running Unit Test: Chatbot Module

This project includes **unit tests** to verify the correctness of core logic, API integrations, and chatbot handling functions.

## 📁 Test File Location

The unit test file is located in the following directory:

```text
Web/testing/
└── test_chatbot.py
```

---

## ⚙️ Test Environment Requirements

Before running the unit tests, please ensure:

- The **virtual environment is activated**
- All dependencies have been installed using:

```bash
pip install -r requirements.txt
```

---

## 🗝️ Required Environment Variables

The unit test file **automatically sets dummy API keys** internally before importing the main module:

```python
os.environ["GOOGLE_API_KEY"] = "TEST_KEY"
os.environ["GEOAPIFY_API_KEY"] = "TEST_KEY"
os.environ["SPOONACULAR_API_KEY"] = "TEST_KEY"
```

📌 **Note:**
- No real API keys are required to run the unit tests.
- External API calls are fully mocked using `unittest.mock`.

---

## ▶️ How to Run the Test

Navigate to the project root directory (**Web/**), then execute:

```bash
python -m unittest testing/test_chatbot.py
```

Alternatively, you may run the test file directly:

```bash
python testing/test_chatbot.py
```

---

## ✅ Test Coverage Overview

The unit tests cover the following components:

- Mathematical helper functions (distance calculation, bounding box)
- Time-based logic (opening hours)
- External API wrappers (Geoapify, Spoonacular) using mocking
- AI-based intent routing (Gemini)
- Restaurant recommendation pipeline
- Daily menu generation
- Main chatbot entry point (`replyToUser`)

All external services (AI, APIs, database) are **mocked**, ensuring the tests run quickly and deterministically.

---

This confirms that the chatbot logic and supporting functions are working as expected.
# 🧪 Running Unit Test: Food Recognition Module

This section explains how to run the unit test for the **FoodRecognition** feature, which is responsible for identifying food names from uploaded images using an AI model.

---

## 📁 Test File Location

The unit test file is located in the `tests/` directory:

```text
tests/
└── test_food_recognition.py
```

This test focuses on validating the behavior of the `replyToImage()` function in `FoodRecognition.py`.

---

## ⚙️ Test Environment Requirements

Before running the test, please make sure that:

- Python **3.12+** is installed
- All dependencies are installed:

```bash
pip install -r requirements.txt
```

The project structure is kept unchanged (especially the relative path between `testing/` and `FoodRecognition.py`)

---

## ▶️ How to Run the Test

From the **project root directory**, run the following command:

```bash
python -m unittest testing/test_food_recognition.py
```

Or, to run all unit tests in the `testing` folder:

```bash
python -m unittest discover testing
```

---

## 🧠 Test Logic Overview

The unit test uses **mocking** to simulate different image inputs and AI responses:

- `unittest.mock.patch` is used to mock the AI model (`GenerativeModel`)
- Image files are simulated using fake binary data (`bytes`)
- Flask application context is manually created for testing API responses

---

## ✅ Test Scenarios Covered
The following cases are tested:
1. **Blurred food image**  
   - Expected result: Correct food name (e.g. *Phở Bò*)
2. **Non-food image (motorbike)**  
   - Expected result: Closest food prediction (*Xôi gấc*)
3. **High-resolution food image**  
   - Expected result: Accurate food name (*Bún giò heo*)
4. **Corrupted or unreadable image**  
   - Expected result: `food_name = "undefined"`
Each test case verifies:
- HTTP status code (`200`)
- Returned JSON structure
- Correctness of the predicted food name

---

## 📌 Notes for Lecturers

- The test does **not** call real AI or external APIs
- All AI responses are mocked to ensure:
  - Deterministic results
  - Fast execution
  - No API key required

This ensures the unit test is **stable**, **repeatable**, and suitable for academic evaluation.

# 🧪 Running Unit Test: Routing Module

This section explains how to run the unit tests for the **Routing** feature, which is responsible for resolving addresses, converting them into geographic coordinates, and generating routes between locations.

The tests focus on validating **edge cases** and **error-handling behavior** of the routing logic.

---

## 📁 Test File Location

The unit test file is located in the `testing/` directory:

```text
testing/
└── test_routing_edge_cases.py
```
This test validates the behavior of the drawPathToDestionation() function implemented in Routing.py.

## ⚙️ Test Environment Requirements
Before running the test, please ensure that:
- Python 3.12+ is installed
- All required dependencies are installed:

```bash
pip install -r requirements.txt
```
- The project structure remains unchanged, especially the relative path between:

```bash
testing/
Routing.py
```
- No real external services (OpenRouteService, geocoding APIs) are required

## ▶️ How to Run the Test
From the project root directory, run:

```bash
python -m unittest testing/test_routing.py
```
To run all unit tests inside the testing folder:

```bash
python -m unittest discover testing
```
## 🧠 Test Logic Overview
The routing unit test is designed to validate robustness, fault tolerance, and edge-case handling of the routing pipeline.
Key techniques used in the test:
- Mocking external dependencies using unittest.mock.patch
- Mocked components include:
  - geocode_address
  - get_coordinates_from_db
  - get_route
- A Flask application context is manually created to allow:
  - JSON responses
  - HTTP status code validation
All test cases are executed without calling real APIs, ensuring:
- Deterministic behavior
- Fast execution
- No API keys required

## ✅ Test Scenarios Covered
The following routing edge cases are tested:

### 1️⃣ Origin address is a number
- Example input:
  - Origin: "12345
  - Destination: Valid address
- Expected behavior:
  - Return HTTP 400
  - Error message indicates invalid address

### 2️⃣ Destination is a strange or meaningless string
- Example input:
  - Origin: Valid address
  - Destination: "skibidi dop dop"
- Expected behavior:
  - Routing continues
  - Destination coordinates are resolved to the closest possible match
  - HTTP 200 returned

### 3️⃣ Origin and destination are identical
- Example input:
  - Origin = Destination
- Expected behavior:
  - Routing proceeds normally
  - Start point and end point coordinates are identical
  - HTTP 200 returned

### 4️⃣ Destination address is ambiguous
- Example input:
  - Destination: "Nguyễn Văn Cừ"
- Expected behavior:
  - Best-matching coordinates are selected
  - HTTP 200 returned

### 5️⃣ Destination address does not exist on the map
- Example input:
  - Destination: "189 Nguyễn Lê Hoàng Khải"
- Expected behavior:
  - Closest valid coordinates are returned
  - HTTP 200 returned

### 6️⃣ Impossible routing scenario (Vietnam → Italy)
- Example input:
  - Origin: Ho Chi Minh City
  - Destination: Italy
- Expected behavior:
  - Routing service throws an exception
  - Exception is caught inside Routing.py
  - HTTP 500 returned
  - Error message includes routing failure reason

## 🔍 Assertions Performed
Each test case verifies:
- HTTP status code (200, 400, or 500)
- Correct JSON response structure
- Correct start_point and end_point coordinates (when applicable)
- Presence of meaningful error messages in failure cases

## 📌 Notes for Lecturers
- All routing, geocoding, and database calls are fully mocked
- Network access is required
- The test suite is:
  - Deterministic
  - Repeatable
  - Safe for academic grading

This unit test ensures that the Routing module behaves correctly under real-world invalid and edge-case inputs, which are common in user-generated location data.