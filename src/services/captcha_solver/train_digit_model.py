import tensorflow as tf
from tensorflow.keras import layers, models
import os

import tensorflow as tf
from tensorflow.keras import layers, models
import os
import argparse
import sys

# Default Constants (Fallback)
DEFAULT_DATASET_DIR = "dataset_digits"
DEFAULT_MODEL_PATH = "src/services/captcha_solver/digit_model.h5"
IMG_SIZE = (32, 32)
BATCH_SIZE = 16
EPOCHS = 35

def main():
    parser = argparse.ArgumentParser(description="Train Digit Model")
    parser.add_argument("--dataset_dir", default=DEFAULT_DATASET_DIR, help="Path to dataset directory")
    parser.add_argument("--model_output", default=DEFAULT_MODEL_PATH, help="Path to save .h5 model")
    parser.add_argument("--tflite_output", default=None, help="Path to save .tflite model (optional)")
    
    args = parser.parse_args()
    
    dataset_dir = args.dataset_dir
    model_output = args.model_output
    
    print(f"Dataset: {dataset_dir}")
    print(f"Output H5: {model_output}")

    if not os.path.exists(dataset_dir):
        print(f"Hata: Dataset klasörü bulunamadı: {dataset_dir}")
        sys.exit(1)

    # Keras'ın built-in loader'ı ile klasörden yükle
    train_ds = tf.keras.preprocessing.image_dataset_from_directory(
        dataset_dir,
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        color_mode='grayscale'
    )

    val_ds = tf.keras.preprocessing.image_dataset_from_directory(
        dataset_dir,
        validation_split=0.2,
        subset="validation",
        seed=123,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        color_mode='grayscale'
    )

    # Normalize et (0-255 -> 0-1)
    normalization_layer = layers.Rescaling(1./255)
    train_ds = train_ds.map(lambda x, y: (normalization_layer(x), y))
    val_ds = val_ds.map(lambda x, y: (normalization_layer(x), y))

    # Model
    model = models.Sequential([
        layers.Input(shape=(32, 32, 1)),
        layers.Conv2D(32, 3, activation='relu'),
        layers.MaxPooling2D(),
        layers.Conv2D(64, 3, activation='relu'),
        layers.MaxPooling2D(),
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dense(10, activation='softmax')
    ])

    model.compile(optimizer='adam',
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                  metrics=['accuracy'])

    model.summary()

    print("Model eğitiliyor...")
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS
    )

    # Dizin yoksa oluştur
    os.makedirs(os.path.dirname(os.path.abspath(model_output)), exist_ok=True)
    
    model.save(model_output)
    print(f"Model kaydedildi: {model_output}")

    # TFLite Dönüşümü
    if args.tflite_output:
        print("\n--- Mobil Dönüşüm Başlatılıyor ---")
        try:
            # We need to import convert dynamically or via sys.path trick if needed
            # But since this script is usually run from root, we can try absolute import
            from src.services.captcha_solver.convert_to_tflite import convert
            convert(model_path=model_output, tflite_path=args.tflite_output)
            
            # If user ONLY wanted tflite? 
            # The script doesn't know that detailed logic, but manager does.
            # Usually tool logic: keep h5 as generic artifact, tflite as export.
            # We keep both unless external tool deletes h5.
            
        except ImportError:
            # Fallback relative import if running next to it
            try:
                from convert_to_tflite import convert
                convert(model_path=model_output, tflite_path=args.tflite_output)
            except Exception as e:
                print(f"Conversion import error: {e}")
        except Exception as e:
             print(f"Conversion error: {e}")

if __name__ == "__main__":
    main()
