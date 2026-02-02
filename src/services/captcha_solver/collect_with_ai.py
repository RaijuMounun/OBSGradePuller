import sys
import os
import time
import uuid
import cv2
import numpy as np
import platform
import subprocess
from rich.console import Console

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir))) # src/services/captcha_solver/ -> src/services/ -> src/ -> root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Correct path adjustment based on where it's run
# If run from root as python src/services/... project_root calculation might be different
# Let's rely on standard python path behaviors or just relative imports if module
# Try to be robust:
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from src.services.obs_client import OBSClient
from src.services.captcha_solver.captcha_solver import CaptchaSolver

class AICollector(CaptchaSolver):
    """Extends CaptchaSolver to return raw digits for data collection."""
    
    def predict_detailed(self, image_path):
        """Returns (d1, d2, d3) digits or None if failed."""
        if not self.model: return None

        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None: return None
            
            digits = []
            for start, end in self.SLICES:
                roi = img[:, start:end]
                h, w = roi.shape
                if w == 0 or h == 0: continue
                
                # Padding & Resize logic mirroring CaptchaSolver
                top_bottom_pad = 0
                left_right_pad = max(0, (h - w) // 2)
                padded = cv2.copyMakeBorder(roi, top_bottom_pad, top_bottom_pad, left_right_pad, left_right_pad, cv2.BORDER_CONSTANT, value=0)
                resized = cv2.resize(padded, (32, 32))
                resized = resized / 255.0 
                
                blob = np.expand_dims(resized, axis=-1)
                blob = np.expand_dims(blob, axis=0)
                
                preds = self.model.predict(blob, verbose=0)
                digit = np.argmax(preds)
                digits.append(digit)
            
            if len(digits) != 3: return None
            return digits
            
        except Exception as e:
            print(f"Prediction Error: {e}")
            return None

def main():
    console = Console()
    client = OBSClient()
    collector = AICollector()
    
    # Check dataset dirs
    dataset_digits_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), "dataset_digits")
    if not os.path.exists(dataset_digits_dir):
        # Fallback if path calc failed, assume run from root
        dataset_digits_dir = "dataset_digits"
        if not os.path.exists(dataset_digits_dir): os.makedirs(dataset_digits_dir)
    
    console.print(f"[bold green]🤖 AI Destekli Veri Toplayıcı[/bold green]")
    console.print(f"Hedef Klasör: [cyan]{dataset_digits_dir}[/cyan]")
    console.print("Kontroller: [bold green]Enter[/bold green] = Onayla & Kaydet, [bold red]f[/bold red] = Yanlış/Atla, [bold red]q[/bold red] = Çıkış\n")

    count = 0
    while True:
        try:
            # 1. Download
            console.print("[dim]Resim indiriliyor...[/dim]", end="\r")
            r_get = client.session.get(client.LOGIN_URL)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r_get.content, "html.parser")
            
            captcha_path = client._download_captcha(soup)
            if not captcha_path:
                time.sleep(1)
                continue
            
            # 2. Predict
            digits = collector.predict_detailed(captcha_path)
            
            # 3. Show Image
            if platform.system() == "Windows": os.startfile(captcha_path)
            elif platform.system() == "Darwin": subprocess.call(("open", captcha_path))
            else: subprocess.call(("xdg-open", captcha_path))
            
            if digits:
                d1, d2, d3 = digits
                prediction_str = f"{d1}{d2} + {d3}"
                console.print(f"📸 Captcha #{count+1} | 🤖 AI Tahmini: [bold cyan]{prediction_str}[/bold cyan]")
            else:
                console.print(f"📸 Captcha #{count+1} | 🤖 AI Tahmini: [red]Başarısız[/red]")
            
            # 4. Ask User
            choice = console.input("Onayla? [Enter/f/q]: ").strip().lower()
            
            if choice == 'q':
                if os.path.exists(captcha_path): os.remove(captcha_path)
                break
            
            if choice == 'f' or not digits:
                console.print("[red]❌ Atlandı (Yanlış Tahmin)[/red]")
                if os.path.exists(captcha_path): os.remove(captcha_path)
                continue
                
            # 5. Save (If Enter)
            console.print("[green]✅ Kaydediliyor...[/green]")
            
            # Re-read for slicing (Reuse logic matches logic in predict, consistent)
            full_img = cv2.imread(captcha_path, cv2.IMREAD_GRAYSCALE)
            
            # SLICES match logic
            SLICES = [(13, 29), (29, 52), (88, 110)]
            
            for i, (start, end) in enumerate(SLICES):
                digit_val = digits[i]
                roi = full_img[:, start:end]
                
                h, w = roi.shape
                if w == 0 or h == 0: continue
                
                top_bottom_pad = 0
                left_right_pad = max(0, (h - w) // 2)
                padded = cv2.copyMakeBorder(roi, top_bottom_pad, top_bottom_pad, left_right_pad, left_right_pad, cv2.BORDER_CONSTANT, value=0)
                resized = cv2.resize(padded, (32, 32))
                
                # Save to specific digit folder
                d_folder = os.path.join(dataset_digits_dir, str(digit_val))
                if not os.path.exists(d_folder): os.makedirs(d_folder)
                
                fname = f"{uuid.uuid4().hex[:8]}.png"
                cv2.imwrite(os.path.join(d_folder, fname), resized)
            
            count += 1
            if os.path.exists(captcha_path): os.remove(captcha_path)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Hata: {e}[/red]")
            time.sleep(1)

if __name__ == "__main__":
    main()
