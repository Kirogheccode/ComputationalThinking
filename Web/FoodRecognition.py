from io import BytesIO
import numpy as np
from tensorflow import keras
from keras.preprocessing import image
from flask import jsonify

MODEL_PATH = "Web/fine_tune_model_best.keras"
TARGET_SIZE = (224, 224)

classes = [
    'Bánh bèo','Bánh bột lọc','Bánh căn','Bánh canh','Bánh chưng','Bánh cuốn',
    'Bánh đúc','Bánh giò','Bánh khọt','Bánh mì','Bánh pía','Bánh tét',
    'Bánh tráng nướng','Bánh xèo','Bún bò Huế','Bún đậu mắm tôm','Bún mắm',
    'Bún riêu','Bún thịt nướng','Cá kho tộ','Canh chua','Cao lầu','Cháo lòng',
    'Cơm tấm','Gỏi cuốn','Hủ tiếu','Mì Quảng','Nem chua','Phở','Xôi xéo'
]

# --- Load model 1 lần duy nhất ---
print("Đang load mô hình món ăn...")
food_model = keras.models.load_model(MODEL_PATH)
print("✔ Mô hình đã load xong!")

# --- API predict ---
def replyToImage(img_file):
    try:

        # --- Dùng BytesIO đọc ảnh trực tiếp ---
        img_bytes = img_file.read()
        img_stream = BytesIO(img_bytes)

        # Load ảnh
        img = image.load_img(img_stream, target_size=TARGET_SIZE)
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0) / 255.0

        # Predict
        pred = food_model.predict(img_array)[0]
        idx = np.argmax(pred)
        confidence = float(pred[idx])
        food_name = classes[idx]

        message = f"Tôi đoán đây là **{food_name}** (xác suất {confidence:.2%})."

        return jsonify({
            "food_name": food_name,
            "confidence": confidence,
            "message": message
        })

    except Exception as e:
        print("Lỗi predict:", e)
        return jsonify({"error": str(e)}), 500