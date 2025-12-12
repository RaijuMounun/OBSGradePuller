import tensorflow as tf
import cv2
import numpy as np
import os
import glob

def verify_tflite():
    tflite_path = "src/services/captcha_solver/digit_model.tflite"
    
    # TFLite Interpreter Yukle
    interpreter = tf.lite.Interpreter(model_path=tflite_path)
    interpreter.allocate_tensors()

    # Input/Output detaylarini al
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    print(f"Input Shape: {input_details[0]['shape']}")
    # Beklenen: [1, 32, 32, 1]

    # Test edecek bir resim bul
    img_paths = glob.glob("dataset/*.png")
    if not img_paths:
        print("Hata: Test edilecek resim bulunamadi (dataset/ bos)")
        return
    
    test_img_path = img_paths[0]
    print(f"Test Resmi: {test_img_path}")

    # --- Preprocessing (Ayni Mantik) ---
    SLICES = [(13, 29), (29, 52), (88, 110)]
    img = cv2.imread(test_img_path, cv2.IMREAD_GRAYSCALE)
    
    digits = []
    
    for start, end in SLICES:
        roi = img[:, start:end]
        
        # Kare yap & Resize
        h, w = roi.shape
        top_bottom_pad = 0
        left_right_pad = max(0, (h - w) // 2)
        padded = cv2.copyMakeBorder(roi, top_bottom_pad, top_bottom_pad, left_right_pad, left_right_pad, cv2.BORDER_CONSTANT, value=0)
        resized = cv2.resize(padded, (32, 32))
        
        # Normalize & Shape
        # TFLite genelde float32 ister (Optimization turune gore degisebilir ama default float32 girdi tutar)
        input_data = resized.astype(np.float32) / 255.0
        input_data = np.expand_dims(input_data, axis=-1) # (32, 32, 1)
        input_data = np.expand_dims(input_data, axis=0)  # (1, 32, 32, 1)

        # --- Inference ---
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])
        
        digit = np.argmax(output_data)
        digits.append(str(digit))

    print(f"🔍 TFLite Tahmini: {digits[0]}{digits[1]} + {digits[2]}")
    print("Eger bu sonuc dogruysa, model mobilde calismaya hazir!")

if __name__ == "__main__":
    verify_tflite()
