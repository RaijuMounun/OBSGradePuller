import sys
import os
import time
import cv2
import numpy as np
import tensorflow as tf
import uuid

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.obs_client import OBSClient

class SmartCaptchaSolver:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "digit_model.h5")
        self.model = self._load_model()
        
    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                return tf.keras.models.load_model(self.model_path, compile=False)
            except Exception as e:
                print(f"Error loading model: {e}")
        return None

    def find_character_regions(self, img_gray):
        """
        Finds potential character regions using contour detection.
        Returns a list of (x, y, w, h) sorted by x coordinate.
        """
        # 1. Threshold
        _, thresh = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 2. Erode lightly to separate touching numbers
        kernel = np.ones((2,2), np.uint8)
        thresh = cv2.erode(thresh, kernel, iterations=1)

        # 3. Find Contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        img_h, img_w = img_gray.shape
        center_x = img_w // 2

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # --- FILTERING LOGIC ---
            
            # 1. Height Filter
            if h < 18:
                continue

            # 2. Plus Sign Specific Filter
            aspect_ratio = w / float(h)
            is_center = (abs(x + w//2 - center_x) < 25) # Close to center
            if is_center and h < 22 and (0.7 < aspect_ratio < 1.4):
                continue

            # 3. Split connected characters
            if w > 28:
                if w > 45: 
                     div = w // 3
                     boxes.append((x, y, div, h))
                     boxes.append((x + div, y, div, h))
                     boxes.append((x + 2*div, y, div, h))
                else: 
                    # Split in half
                    boxes.append((x, y, w // 2, h))
                    boxes.append((x + w // 2, y, w // 2, h))
            else:
                boxes.append((x, y, w, h))
                
        # Sort left-to-right
        boxes.sort(key=lambda b: b[0])
        
        # Limit to max 3 items
        boxes = boxes[:3]
        
        return boxes

    def predict_digit(self, roi):
        if self.model is None: return "?"
        
        # Preprocess
        h, w = roi.shape
        if h == 0 or w == 0: return "?"
        
        top_bottom_pad = 0
        left_right_pad = max(0, (h - w) // 2)
        padded = cv2.copyMakeBorder(roi, top_bottom_pad, top_bottom_pad, left_right_pad, left_right_pad, cv2.BORDER_CONSTANT, value=0)
        
        resized = cv2.resize(padded, (32, 32))
        normalized = resized / 255.0
        
        blob = np.expand_dims(normalized, axis=-1)
        blob = np.expand_dims(blob, axis=0)
        
        preds = self.model.predict(blob, verbose=0)
        return str(np.argmax(preds))

def main():
    print("Starting Automated Data Collection (100 Samples)...")
    
    # Setup dataset directory
    dataset_digits_dir = os.path.join(project_root, "dataset_digits")
    if not os.path.exists(dataset_digits_dir):
        os.makedirs(dataset_digits_dir)
        print(f"Created directory: {dataset_digits_dir}")
        for i in range(10):
            os.makedirs(os.path.join(dataset_digits_dir, str(i)), exist_ok=True)
        
    client = OBSClient()
    solver = SmartCaptchaSolver()
    
    success_count = 0
    total_samples = 50
    
    for i in range(total_samples):
        try:
            print(f"[{i+1}/{total_samples}] Downloading...", end="\r")
            
            # Download
            r_get = client.session.get(client.LOGIN_URL)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r_get.content, "html.parser")
            captcha_path = client._download_captcha(soup)
            
            if not captcha_path:
                print(f"[{i+1}/{total_samples}] Download failed, skipping.")
                continue
                
            # Process
            img_gray = cv2.imread(captcha_path, cv2.IMREAD_GRAYSCALE)
            if img_gray is None:
                if os.path.exists(captcha_path): os.remove(captcha_path)
                continue

            img_h, img_w = img_gray.shape
            boxes = solver.find_character_regions(img_gray)
            
            # If no digits found, skip
            if not boxes:
                if os.path.exists(captcha_path): os.remove(captcha_path)
                continue

            parsed_digits = ""
            for x, y, w, h in boxes:
                # Add Padding (3px)
                pad = 3
                x_start = max(0, x - pad)
                x_end = min(img_w, x + w + pad)
                
                # Full height slice
                roi = img_gray[0:img_h, x_start:x_end]
                
                # Predict
                digit_label = solver.predict_digit(roi)
                if digit_label == "?": continue
                parsed_digits += digit_label
                
                # Resize to 32x32 before saving (Standardize dataset)
                # Note: collect_data.py was doing padding+resize. We should stick to that standard.
                # Re-using the preprocessing logic from predict_digit for resizing but returning the image
                roi_h, roi_w = roi.shape
                t_b_pad = 0
                l_r_pad = max(0, (roi_h - roi_w) // 2)
                padded_roi = cv2.copyMakeBorder(roi, t_b_pad, t_b_pad, l_r_pad, l_r_pad, cv2.BORDER_CONSTANT, value=0)
                final_img = cv2.resize(padded_roi, (32, 32))

                # Save to dataset_digits/{label}/{uuid}.png
                save_dir = os.path.join(dataset_digits_dir, digit_label)
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                
                save_filename = f"{uuid.uuid4().hex[:12]}.png"
                cv2.imwrite(os.path.join(save_dir, save_filename), final_img)
            
            print(f"[{i+1}/{total_samples}] Parsed: {parsed_digits} | Saved to dataset       ")
            success_count += 1
            
            # Cleanup
            if os.path.exists(captcha_path):
                os.remove(captcha_path)
                
            # Nice sleep to avoid hammering the server
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            continue

    print(f"\nCompleted! Successfully processed {success_count} captchas.")

if __name__ == "__main__":
    main()
