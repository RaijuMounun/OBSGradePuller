import sys
import os
import time

# Bu kod, main.py nereden çalıştırılırsa çalıştırılsın 'src' modülünün bulunmasını sağlar.
current_dir = os.path.dirname(os.path.abspath(__file__)) # src/
project_root = os.path.dirname(current_dir)            # OBSGradePuller/
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from rich.progress import Progress, SpinnerColumn, TextColumn

# Kendi modüllerimizi import ediyoruz
from src.services.auth_manager import AuthManager
from src.services.obs_client import OBSClient
from src.services.captcha_solver.captcha_solver import CaptchaSolver
from src.ui.display import DisplayManager

def main():
    # 1. YÖNETİCİLERİ BAŞLAT
    ui = DisplayManager()
    auth = AuthManager()
    client = OBSClient()
    
    ui.print_banner()

    # 2. KULLANICI SEÇİMİ VE GİRİŞ (AUTH FLOW)
    current_user = None
    current_pass = None

    registered_users = auth.get_registered_users()
    
    # Eğer kayıtlı kullanıcı varsa sor: "Kimsin?"
    if registered_users:
        choices = registered_users + ["Yeni Giriş Yap", "Kullanıcı Sil", "Çıkış"]
        choice = ui.ask_choice("Kullanıcı Seçimi", choices)

        if choice == "Çıkış":
            ui.show_message("Güle güle!", "yellow")
            sys.exit(0)
        
        elif choice == "Yeni Giriş Yap":
            # Yeni kullanıcı akışına düşecek (aşağıda)
            pass
            
        elif choice == "Kullanıcı Sil":
            user_to_delete = ui.ask_choice("Silinecek Kullanıcı", registered_users)
            auth.delete_user(user_to_delete)
            ui.show_message(f"{user_to_delete} silindi.", "red")
            # Silince tekrar başa dönmek en temizi (recursive main çağrısı yerine loop kullanılabilir ama basit olsun)
            return main()

        else:
            # Kayıtlı kullanıcı seçildi
            current_user = choice
            current_pass = auth.get_password(current_user)
            if not current_pass:
                ui.show_message("Hata: Kayıtlı şifre okunamadı!", "red")
                current_user = None # Yeni girişe zorla

    # Eğer kullanıcı seçilmediyse veya yeni giriş ise
    save_credentials = False
    if not current_user:
        ui.show_message("Lütfen OBS bilgilerinle giriş yap", "cyan")
        current_user = ui.ask_input("Öğrenci No")
        current_pass = ui.ask_input("Şifre", password=True)
        save_credentials = True # Başarılı olursa soracağız

    # 3. OBS LOGIN İŞLEMİ
    login_success = False
    
    # Login Loading Animasyonu
    with ui.console.status("[bold green]OBS Sistemine Bağlanılıyor...", spinner="dots") as status:
        try:
            def captcha_handler(path):
                # 1. Önce AI ile çözmeye çalış
                ai_result = None
                try:
                    solver = CaptchaSolver()
                    ai_result = solver.solve(path)
                except Exception as err:
                    # Model hatası varsa yut, manuele düş
                    pass 
                
                # EĞER AI ÇÖZDÜYSE DİREKT DÖNDÜR (OTOMASYON)
                if ai_result:
                    ui.console.print(f"[bold cyan]🤖 AI Otomatik Çözdü: {ai_result}[/bold cyan]")
                    # Kısa bir bekleme (opsiyonel, kullanıcının görmesi için)
                    import time
                    time.sleep(0.5)
                    return ai_result

                # --- AI BAŞARISIZ İSE MANUEL GİRİŞ ---
                ui.console.print("[yellow]⚠️ AI Okuyamadı, Manuel Giriş Gerekiyor![/yellow]")
                
                # Resmi işletim sisteminde aç
                import os, subprocess, platform
                if platform.system() == "Windows": os.startfile(path)
                elif platform.system() == "Darwin": subprocess.call(("open", path))
                else: subprocess.call(("xdg-open", path))
                
                ui.console.print(f"[yellow]Captcha açıldı ({path})...[/yellow]")
                
                # --- KRİTİK HAMLE: Animasyonu durdur ---
                status.stop()
                
                prompt = "Captcha Kodu"
                code = ui.ask_input(prompt)
                
                # Input bitti, animasyonu tekrar başlat
                status.start()
                # ---------------------------------------
                
                return code

            login_success = client.login(current_user, current_pass, captcha_handler)
            
        except Exception as e:
            # Hata mesajı basmadan önce status'ü durdurmak gerekebilir ama
            # with bloğu çıkışta otomatik kapatır. Yine de garanti olsun:
            status.stop()
            ui.show_message(f"Bağlantı Hatası: {str(e)}", "red")
            return

    if not login_success:
        ui.show_message("❌ Giriş Başarısız! Kullanıcı adı, şifre veya captcha hatalı.", "red")
        # Hatalı girişse ve kayıtlıysa, belki silmek istersin? (Opsiyonel)
        return

    ui.show_message(f"✅ Giriş Başarılı: {current_user}", "green")

    # 4. ŞİFRE KAYDETME SORUSU (Sadece yeni girişse)
    if save_credentials:
        if ui.ask_choice("Bilgileri güvenli kasaya (Keyring) kaydedeyim mi?", ["Evet", "Hayır"]) == "Evet":
            auth.save_user(current_user, current_pass)
            ui.show_message("Bilgiler kaydedildi!", "green")

    # 5. VERİ ÇEKME VE GÖSTERME
    try:
        # Rich Progress Bar ile veri çekme animasyonu
        grades = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task("[green]Ders notları ve ortalamalar çekiliyor...", total=None)
            
            # OBSClient bizim için her şeyi (Notlar + AJAX Ortalamaları) hallediyor
            grades = client.fetch_grades()
            
            progress.update(task, completed=100)

        # Tabloyu çiz
        # Dönem bilgisini grades listesindeki ilk elemandan alabiliriz (hepsi aynı dönemdir)
        term_id = grades[0].term_id if grades else "Bilinmiyor"
        ui.render_grades(grades, term_id)

    except Exception as e:
        ui.show_message(f"Veri Çekme Hatası: {str(e)}", "red")
        import traceback
        traceback.print_exc() # Detaylı hata (Geliştirme aşamasında açık kalsın)

    # 6. ÇIKIŞ
    ui.console.print("\n")
    if ui.ask_choice("Ne yapmak istersin?", ["Kullanıcı Değiştir", "Çıkış"]) == "Kullanıcı Değiştir":
        main() # Rekürsif çağrı ile başa dön
    else:
        ui.show_message("İyi çalışmalar!", "yellow")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nİşlem iptal edildi.")