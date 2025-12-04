
import os
from flask import jsonify
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GOOGLE_API = os.getenv("GOOGLE_API")

if GOOGLE_API:
    genai.configure(api_key=GOOGLE_API)
else:
    print("Error: GOOGLE_API_KEY not found. Please check your .env file.")
    exit()

def replyToImage(img_file):
    try:
        # Đọc ảnh raw bytes
        img_bytes = img_file.read()

        prompt = (
            "Bạn là hệ thống nhận diện món ăn Việt Nam. "
            "Chỉ trả về đúng 1 tên món ăn trong danh sách sau đây, không mô tả thêm:\n\n"
            "Nếu món ăn không có trong danh sách, hãy chọn món giống nhất."
        )

        model = genai.GenerativeModel("gemini-2.5-flash")

        response = model.generate_content([
            prompt,
            {"mime_type": img_file.mimetype, "data": img_bytes}
        ])

        food_name = response.text.strip()
        message = f"The food you are looking for is {food_name}."

        return jsonify({
            "food_name": food_name,
            "message": message
        })

    except Exception as e:
        print("Lỗi AI predict:", e)
        return jsonify({"error": str(e)}), 500
