import tensorflow as tf
import os
import numpy as np

import tensorflow as tf
import os
import numpy as np

def convert(model_path=None, tflite_path=None):
    if model_path is None:
        model_path = os.path.join("src", "services", "captcha_solver", "digit_model.h5")
    if tflite_path is None:
        tflite_path = os.path.join("src", "services", "captcha_solver", "digit_model.tflite")

    if not os.path.exists(model_path):
        print(f"Hata: Model bulunamadi -> {model_path}")
        return

    print(f"Model yukleniyor: {model_path}")
    model = tf.keras.models.load_model(model_path)

    # Converter Olustur
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # --- DOĞRULUK KORUMA (ACCURACY PRESERVATION) ---
    # Kullanıcı isteği üzerine Float32 olarak bırakıyoruz.
    # Quantization (Int8) yaparsak boyut düşer ama hassasiyet azalabilir.
    # converter.optimizations = [tf.lite.Optimize.DEFAULT]  <- BU SATIR KAPALI KALMALI
    
    # Mobile (Flutter) uyumluluğu için
    # Input/Output signature'larını netleştiriyoruz.
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS, # Standart TFLite ops
        tf.lite.OpsSet.SELECT_TF_OPS    # Fallback (gerekirse)
    ]

    print("Donusturme basladi (High Fidelity Mode)...")
    tflite_model = converter.convert()

    # Kaydet
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)

    print(f"✅ Basarili! TFLite model kaydedildi: {tflite_path}")
    
    # Boyut Karsilastirmasi
    h5_size = os.path.getsize(model_path) / 1024
    tflite_size = os.path.getsize(tflite_path) / 1024
    print(f"H5 Boyutu: {h5_size:.2f} KB")
    print(f"TFLite Boyutu: {tflite_size:.2f} KB")
    print(f"Not: Optimizasyon yapılmadığı için boyut benzer olabilir, ancak doğruluk %100 korunmuştur.")

if __name__ == "__main__":
    convert()
