import numpy as np
from tensorflow import keras
from tensorflow.keras.preprocessing import image

# --- Cấu hình ---
MODEL_PATH = "Path to model" 
IMAGE_PATH = "Path to picture"                    
TARGET_SIZE = (300, 300)                    # kích thước ảnh khi train

LABELS = None   

classes = [
    'Bánh bèo',
    'Bánh bột lọc',
    'Bánh căn',
    'Bánh canh',
    'Bánh chưng',
    'Bánh cuốn',
    'Bánh đúc',
    'Bánh giò',
    'Bánh khọt',
    'Bánh mì',
    'Bánh pía',
    'Bánh tét',
    'Bánh tráng nướng',
    'Bánh xèo',
    'Bún bò Huế',
    'Bún đậu mắm tôm',
    'Bún mắm',
    'Bún riêu',
    'Bún thịt nướng',
    'Cá kho tộ',
    'Canh chua',
    'Cao lầu',
    'Cháo lòng',
    'Cơm tấm',
    'Gỏi cuốn',
    'Hủ tiếu',
    'Mì Quảng',
    'Nem chua',
    'Phở',
    'Xôi xéo'
]

# --- Load model ---
model = keras.models.load_model(MODEL_PATH)
print("Đã load mô hình thành công!")

# --- Load & preprocess ---
img = image.load_img(IMAGE_PATH, target_size=TARGET_SIZE)
img_array = image.img_to_array(img)
img_array = np.expand_dims(img_array, axis=0)
img_array = img_array / 255.0

# --- Predict ---
pred = model.predict(img_array)
pred = pred[0]

# Lấy lớp có xác suất cao nhất
class_index = np.argmax(pred)
confidence = pred[class_index]

print("Chỉ số lớp:", class_index)
print("Xác suất:", confidence)

if LABELS:
    print("Dự đoán:", LABELS[class_index])
else:
    print("Dự đoán: class", classes[class_index])