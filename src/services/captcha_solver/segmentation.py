import cv2
import numpy as np
from typing import List, Tuple

class CaptchaSegmentationService:
    """
    Shared service for splitting captcha images into digit regions.
    Uses strict rules (Threshold -> Erode -> Contours -> Filter) to ensure
    what the user labels is EXACTLY what the model sees.
    """

    @staticmethod
    def find_character_regions(img_gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Finds potential character regions using contour detection.
        Returns a list of (x, y, w, h) sorted by x coordinate.
        
        Args:
            img_gray: Grayscale image (numpy array)
            
        Returns:
            List of tuples (x, y, w, h) bounding boxes.
        """
        if img_gray is None: return []

        # 1. Threshold
        # OTSU thresholding automatic olarak en iyi eşik değerini bulur
        _, thresh = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 2. Erode lightly to separate touching numbers
        # Rakamlar birbirine çok yakınsa/bitişikse ayırmak için erozyon uygulanır
        kernel = np.ones((2,2), np.uint8)
        thresh = cv2.erode(thresh, kernel, iterations=1)

        # 3. Find Contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        img_h, img_w = img_gray.shape
        center_x = img_w // 2

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # --- FILTERING LOGIC (STRICT) ---
            
            # 1. Height Filter (Gürültü ve küçük noktalar için)
            if h < 18:
                continue

            # 2. Plus Sign Specific Filter (Artı işaretini elemek için)
            # Genelde ortada bulunur, kareye yakındır ve belirli bir boyuttadır
            aspect_ratio = w / float(h)
            is_center = (abs(x + w//2 - center_x) < 25) # Close to center
            if is_center and h < 22 and (0.7 < aspect_ratio < 1.4):
                continue

            # 3. Split connected characters (Bitişik rakamları ayırma)
            if w > 28:
                if w > 45: 
                    # 3 parça ihtimali (Çok geniş blob)
                     div = w // 3
                     boxes.append((x, y, div, h))
                     boxes.append((x + div, y, div, h))
                     boxes.append((x + 2*div, y, div, h))
                else: 
                    # 2 parça ihtimali (Geniş blob)
                    boxes.append((x, y, w // 2, h))
                    boxes.append((x + w // 2, y, w // 2, h))
            else:
                # Normal rakam
                boxes.append((x, y, w, h))
                
        # Sort left-to-right (Soldan sağa sıralama çok önemli)
        boxes.sort(key=lambda b: b[0])
        
        # Limit to max 3 items (Beklenen format: XX+X veya X+X)
        boxes = boxes[:3]
        
        return boxes

    @staticmethod
    def preprocess_for_model(roi: np.ndarray, target_size=(32, 32)) -> np.ndarray:
        """
        Prepares a region of interest (ROI) for model inference.
        Square padding + Resize + Normalization.
        """
        h, w = roi.shape
        if h == 0 or w == 0: return None
        
        # Square Pad (Kareleştirme)
        top_bottom_pad = 0
        left_right_pad = max(0, (h - w) // 2)
        padded = cv2.copyMakeBorder(roi, top_bottom_pad, top_bottom_pad, left_right_pad, left_right_pad, cv2.BORDER_CONSTANT, value=0)
        
        # Resize
        resized = cv2.resize(padded, target_size)
        
        # Normalize (0.0 - 1.0)
        normalized = resized / 255.0
        
        # Expand dims for Keras Input (1, 32, 32, 1)
        blob = np.expand_dims(normalized, axis=-1)
        blob = np.expand_dims(blob, axis=0)
        
        return blob
