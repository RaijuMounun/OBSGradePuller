import keyring
import json
import os
from typing import List, Optional
from src.models import UserProfile

class AuthManager:
    SERVICE_ID = "OBS_Grade_Puller_App"
    PROFILE_FILE = "profiles.json"

    def __init__(self):
        self._profiles = self._load_profiles()

    def _load_profiles(self) -> List[str]:
        """Kayıtlı kullanıcı adlarını JSON'dan yükler."""
        if not os.path.exists(self.PROFILE_FILE):
            return []
        try:
            with open(self.PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def _save_profiles(self):
        """Kullanıcı listesini JSON'a yazar."""
        with open(self.PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._profiles, f)

    def save_user(self, username: str, password: str):
        """Kullanıcıyı listeye ekler, şifreyi Keyring'e kilitler."""
        # 1. Şifreyi güvenli kasaya koy
        keyring.set_password(self.SERVICE_ID, username, password)
        
        # 2. Listede yoksa ekle
        if username not in self._profiles:
            self._profiles.append(username)
            self._save_profiles()

    def get_password(self, username: str) -> Optional[str]:
        """Verilen kullanıcının şifresini kasadan çeker."""
        return keyring.get_password(self.SERVICE_ID, username)

    def get_registered_users(self) -> List[str]:
        """Kayıtlı kullanıcıların listesini döner."""
        return self._profiles

    def delete_user(self, username: str):
        """Kullanıcıyı hem listeden hem kasadan siler."""
        # Kasadan sil
        try:
            keyring.delete_password(self.SERVICE_ID, username)
        except:
            pass # Zaten yoksa hata verme

        # Listeden sil
        if username in self._profiles:
            self._profiles.remove(username)
            self._save_profiles()