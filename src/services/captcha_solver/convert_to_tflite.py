import tensorflow as tf
import os
import numpy as np

def convert_to_tflite():
    # H5 Model Yolu
    model_path = os.path.join("src", "services", "captcha_solver", "digit_model.h5")
    tflite_path = os.path.join("src", "services", "captcha_solver", "digit_model.tflite")

    if not os.path.exists(model_path):
        print(f"Hata: Model bulunamadi -> {model_path}")
        return

    print(f"Model yukleniyor: {model_path}")
    model = tf.keras.models.load_model(model_path)

    # Converter Olustur
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # Optimizasyonlar (Opsiyonel ama mobilde iyidir)
    # Default optimizations: Quantization vb. yapar (boyutu kucultur)
    # KULLANICI ISTEGI: Accuracy kaybi olmamasi icin optimizasyonu kapatiyoruz.
    # converter.optimizations = [tf.lite.Optimize.DEFAULT]

    print("Donusturme basladi...")
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
    print(f"Sıkılaştırma Oranı: %{100 * (1 - tflite_size/h5_size):.1f}")

if __name__ == "__main__":
    convert_to_tflite()
