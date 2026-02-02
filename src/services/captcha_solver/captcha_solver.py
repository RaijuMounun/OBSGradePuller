import tensorflow as tf
import cv2
import numpy as np
import os

class CaptchaSolver:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "digit_model.h5")

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.MODEL_PATH):
            try:
                self.model = tf.keras.models.load_model(self.MODEL_PATH, compile=False)
                print("[INFO] Rakam Modeli Yüklendi.")
            except Exception as e:
                print(f"[HATA] Model yüklenemedi: {e}")
        else:
            print("[UYARI] Model dosyası bulunamadı.")

    def find_character_regions(self, img_gray):
        """
        Proxy method to keep backward compatibility or direct usage,
        delegating to the shared service.
        """
        from .segmentation import CaptchaSegmentationService
        return CaptchaSegmentationService.find_character_regions(img_gray)

    def predict_digit_from_roi(self, roi):
        if self.model is None: return None
        
        from .segmentation import CaptchaSegmentationService
        blob = CaptchaSegmentationService.preprocess_for_model(roi)
        
        if blob is None: return None
        
        preds = self.model.predict(blob, verbose=0)
        return np.argmax(preds)

    def solve(self, image_path: str) -> str:
        if not self.model:
            return None

        try:
            # 1. Read Image
            img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img_gray is None: return None
            
            img_h, img_w = img_gray.shape

            # 2. Smart Segmentation (Delegated)
            boxes = self.find_character_regions(img_gray)
            
            if len(boxes) < 2:
                print(f"[UYARI] Yeterli rakam bulunamadı: {len(boxes)}")
                # Debug icin kaydet
                # cv2.imwrite("debug_failed_segmentation.png", img_gray)
                return None

            digits = []
            for x, y, w, h in boxes:
                # Add Padding (3px)
                pad = 3
                x_start = max(0, x - pad)
                x_end = min(img_w, x + w + pad)
                
                # Full height slice
                roi = img_gray[0:img_h, x_start:x_end]
                
                digit = self.predict_digit_from_roi(roi)
                if digit is not None:
                    digits.append(digit)
            
            # 3. Calculate Result
            # Logic: XX + X (3 digits) or X + X (2 digits)
            result = 0
            
            print(f"[AI RAW] Algılanan Rakamlar: {digits}")

            if len(digits) == 3:
                # xx + x
                num1 = (digits[0] * 10) + digits[1]
                num2 = digits[2]
                result = num1 + num2
            elif len(digits) == 2:
                # x + x
                num1 = digits[0]
                num2 = digits[1]
                result = num1 + num2
            else:
                return None

            print(f"[AI TAHMİN] Sonuç: {result}")
            return str(result)
            
        except Exception as e:
            print(f"[HATA] Çözüm hatası: {e}")
            return None
