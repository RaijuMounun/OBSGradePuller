from dataclasses import dataclass
from typing import Optional

@dataclass
class ExamStats:
    """Tek bir sınavın notu ve sınıf ortalaması."""
    score: str = "-"       # Öğrencinin notu (Örn: 80)
    class_avg: str = "?"   # Sınıf ortalaması (Örn: 44,90)

@dataclass
class CourseGrade:
    """Bir dersin tüm not bilgileri."""
    code: str              # Ders Kodu (BİLM201)
    name: str              # Ders Adı (Sayısal Tasarım)
    midterm: ExamStats     # Vize
    final: ExamStats       # Final
    makeup: ExamStats      # Bütünleme
    letter_grade: str      # Harf Notu (AA, BA, --)
    term_id: str           # Dönem ID (20251)

@dataclass
class UserProfile:
    """Kullanıcı profil bilgisi (Şifre burada tutulmaz!)."""
    username: str          # Öğrenci No
    last_login: str = ""   # Son giriş tarihi (Opsiyonel, şimdilik boş kalsın)