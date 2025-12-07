import asyncio
import os
import platform
import subprocess
import json
from typing import List, Callable, Optional
from dataclasses import dataclass, asdict
import time

from playwright.async_api import async_playwright
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

# --- 1. ÖZEL HATA SINIFLARI (Exception Handling) ---
class CaptchaError(Exception):
    """Sadece Captcha yanlış girildiğinde fırlatılır."""
    pass

class CredentialError(Exception):
    """Kullanıcı adı veya şifre yanlış olduğunda fırlatılır."""
    pass

# --- 2. VERİ MODELLERİ ---
@dataclass
class StudentGrade:
    course_name: str
    midterm: str
    final: str
    letter_grade: str

@dataclass
class UserConfig:
    username: str
    password: str

# --- 3. CONFIG MANAGER ---
class ConfigManager:
    FILE_NAME = "user_config.json"

    @staticmethod
    def load() -> Optional[UserConfig]:
        if not os.path.exists(ConfigManager.FILE_NAME):
            return None
        try:
            with open(ConfigManager.FILE_NAME, "r", encoding="utf-8") as f:
                data = json.load(f)
                return UserConfig(**data)
        except:
            return None

    @staticmethod
    def save(config: UserConfig):
        with open(ConfigManager.FILE_NAME, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f)

    @staticmethod
    def delete():
        if os.path.exists(ConfigManager.FILE_NAME):
            os.remove(ConfigManager.FILE_NAME)

# --- 4. ARAYÜZ KATMANI (UI) ---
class TerminalUI:
    def __init__(self):
        self.console = Console()

    def show_captcha(self, image_path: str) -> str:
        self.console.print(f"[yellow]! Güvenlik resmi açılıyor...[/yellow]")
        
        if platform.system() == "Windows":
            os.startfile(image_path)
        elif platform.system() == "Darwin":
            subprocess.call(("open", image_path))
        else:
            subprocess.call(("xdg-open", image_path))

        return Prompt.ask("[bold cyan]Resimdeki kodu girin[/bold cyan]")

    def display_grades(self, grades: List[StudentGrade]):
        if not grades:
            self.console.print("[red]Görüntülenecek not bulunamadı![/red]")
            return

        table = Table(title="🎓 Dönem Notları", border_style="blue", header_style="bold magenta")
        table.add_column("Ders Adı", style="cyan", no_wrap=True)
        table.add_column("Vize", justify="center")
        table.add_column("Final", justify="center")
        table.add_column("Harf", justify="center", style="bold")

        for grade in grades:
            color = "red" if grade.letter_grade in ["FF", "FD", "DZ"] else "green"
            formatted_grade = f"[{color}]{grade.letter_grade}[/{color}]"
            table.add_row(grade.course_name, grade.midterm, grade.final, formatted_grade)

        self.console.print(table)
        
    def show_error(self, message: str):
        self.console.print(Panel(message, title="Hata", style="bold red"))
        
    def show_success(self, message: str):
        self.console.print(f"[bold green]✅ {message}[/bold green]")
        
    def show_warning(self, message: str):
        self.console.print(f"[bold yellow]⚠️ {message}[/bold yellow]")

# --- 5. SCRAPER SERVİSİ (Logic) ---
class UniversityScraper:
    def __init__(self, login_url: str):
        self.login_url = login_url

    async def fetch_grades(self, user_config: UserConfig, captcha_callback: Callable[[str], str]) -> List[StudentGrade]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()

            try:
                # --- A. GİRİŞ İŞLEMLERİ ---
                print("Login sayfasına gidiliyor...")
                await page.goto(self.login_url)
                
                await page.fill("#txtParamT01", user_config.username)

                # Şifre kilidini kır ve yaz
                await page.click("#txtParamT02", force=True)
                await page.evaluate("document.getElementById('txtParamT02').removeAttribute('readonly')")
                await page.fill("#txtParamT02", user_config.password)   

                # Captcha varsa hallet
                if await page.locator("#imgCaptchaImg").count() > 0:
                    temp_img = "captcha.png"
                    await page.locator("#imgCaptchaImg").screenshot(path=temp_img)
                    code = captcha_callback(temp_img) 
                    
                    # Captcha'yı yazıyoruz
                    await page.fill("#txtSecCode", code) 
                    
                    # Site bazen input'tan çıkınca (blur) işlem yapıyor, tetiklemek için boş yere tıkla
                    await page.click("body", force=True)

                    if os.path.exists(temp_img): os.remove(temp_img)

                # --- DÜZELTME: BUTON BEKLEME ---
                print("Giriş butonunun aktif olması bekleniyor...")
                # CSS Selector Mantığı: ID'si btnLogin olan AMA class'ında 'disabled' OLMAYAN elementi bekle.
                try:
                    await page.wait_for_selector("#btnLogin:not(.disabled)", state="visible", timeout=15000)
                except:
                    print("⚠️ Uyarı: Buton hala 'disabled' görünüyor, yine de şansımızı deniyoruz...")

                print("Giriş butonuna basıldı, yanıt bekleniyor...")
                # force=True ekledik ki önünde görünmez bir engel varsa bile bassın
                await page.click("#btnLogin", force=True) 
                
                # --- AKILLI BEKLEME (POLLING) BAŞLANGICI ---
                max_retries = 20
                login_success = False
                
                for _ in range(max_retries):
                    # 1. Başarılı Giriş Kontrolü
                    if "login.aspx" not in page.url:
                        login_success = True
                        print("URL değişti, giriş başarılı kabul ediliyor.")
                        break

                    # 2. Hata Mesajı Kontrolü
                    try:
                        body_text = (await page.inner_text("body")).lower()
                        
                        if "güvenlik kodu hatalı" in body_text or "hatalı girildi" in body_text:
                            raise CaptchaError("Güvenlik kodu (Captcha) yanlış girildi.")
                        
                        if ("kullanıcı adı" in body_text or "şifre" in body_text) and "hatalı" in body_text:
                            raise CredentialError("Öğrenci numarası veya şifre hatalı.")
                        
                        if await page.locator(".swal2-content").count() > 0:
                            popup_text = (await page.locator(".swal2-content").inner_text()).lower()
                            if "güvenlik" in popup_text:
                                raise CaptchaError("Güvenlik kodu yanlış girildi.")
                            if "şifre" in popup_text or "kullanıcı" in popup_text:
                                raise CredentialError("Bilgiler hatalı.")

                    except (CaptchaError, CredentialError):
                        raise
                    except:
                        pass

                    await page.wait_for_timeout(500)

                if "login.aspx" in page.url and not login_success:
                    raise Exception("Giriş zaman aşımına uğradı veya buton tepki vermedi.")
                
                # --- AKILLI BEKLEME BİTİŞİ ---

                print("Giriş başarılı! Menüye gidiliyor...")

                # --- C. MENÜYE GİTME (Native Click) ---
                target_link = page.locator("a:has-text('Not Listesi')")
                await target_link.wait_for(state="attached", timeout=10000)
                await target_link.evaluate("element => element.click()")

                # --- D. POPUP SAVAR ---
                try:
                    popup_btn = page.locator("button.swal2-confirm")
                    if await popup_btn.count() > 0:
                         await popup_btn.click(timeout=2000)
                         await page.wait_for_timeout(500)
                except:
                    pass 

                # --- E. IFRAME İÇİNDE TABLO ARAMA ---
                print("Tablo aranıyor...")
                content_frame = None
                
                try:
                    await page.wait_for_selector("#grd_not_listesi", state="attached", timeout=2000)
                    content_frame = page
                except:
                    pass

                if not content_frame:
                    for frame in page.frames:
                        try:
                            if await frame.locator("#grd_not_listesi").count() > 0:
                                content_frame = frame
                                break
                        except:
                            continue
                
                if not content_frame:
                    raise Exception("Tablo bulunamadı! (Giriş yapılmış olsa bile tablo yüklenmedi)")

                # --- F. VERİYİ OKUMA ---
                rows = await content_frame.locator("#grd_not_listesi tbody tr").all()
                grades = []

                for row in rows:
                    cols = await row.locator("td").all()
                    if len(cols) > 5:
                        course_text = await cols[2].inner_text()
                        if not course_text.strip() or "Ders Adı" in course_text: continue

                        course = course_text.strip()
                        exam_info = (await cols[4].inner_text()).strip() 
                        letter = (await cols[6].inner_text()).strip()
                        
                        midterm = "-"
                        if "Vize" in exam_info:
                            parts = exam_info.split(":")
                            if len(parts) > 1: midterm = parts[1].strip().split()[0]

                        final = "-"
                        if not letter: letter = "--"

                        grades.append(StudentGrade(course, midterm, final, letter))
                
                return grades

            except (CaptchaError, CredentialError):
                raise 
            except Exception as e:
                raise e
            finally:
                await browser.close()

# --- 6. ANA PROGRAM (YENİ AKIŞ) ---
async def main():
    ui = TerminalUI()
    scraper = UniversityScraper(login_url="https://obs.ozal.edu.tr/oibs/std/login.aspx")

    # --- DIŞ DÖNGÜ: KİMLİK BİLGİLERİ ---
    while True:
        # 1. Config Yükle veya İste
        user_config = ConfigManager.load()
        is_from_file = True

        if user_config:
            ui.console.print(f"\n[green]Kayıtlı kullanıcı: {user_config.username}[/green]")
            if not Confirm.ask("Bu kullanıcı ile devam edilsin mi?"):
                ConfigManager.delete()
                user_config = None
                is_from_file = False
        else:
            is_from_file = False

        if not user_config:
            username = Prompt.ask("Öğrenci No")
            password = Prompt.ask("Şifre", password=True)
            user_config = UserConfig(username, password)
            # DİKKAT: Burada hemen kaydetmiyoruz! Giriş başarılı olursa kaydedeceğiz.

        # --- İÇ DÖNGÜ: CAPTCHA / GİRİŞ DENEMESİ ---
        while True:
            ui.console.print("\n[yellow]Sisteme bağlanılıyor...[/yellow]")
            
            try:
                # Scraper'ı çalıştır
                grades = await scraper.fetch_grades(user_config, ui.show_captcha)
                
                # --- BAŞARILI OLURSA ---
                ui.show_success("Giriş Başarılı! Notlar alındı.")
                ui.display_grades(grades)

                # Eğer dosyalardan gelmediyse (yeni girişse) ve başarılı olduysa ŞİMDİ KAYDET
                if not is_from_file:
                    if Confirm.ask("Bilgiler 'user_config.json' dosyasına kaydedilsin mi?"):
                        ConfigManager.save(user_config)
                        ui.show_success("Bilgiler kaydedildi.")
                
                return # Programdan çık

            except CaptchaError:
                # Sadece Captcha yanlışsa
                ui.show_warning("Güvenlik kodu (Captcha) yanlış girildi!")
                if Confirm.ask("Tekrar denemek ister misin? (Bilgileri tekrar girmene gerek yok)"):
                    continue # İç döngünün başına dön (UserConfig aynı kalır)
                else:
                    return # Çıkış

            except CredentialError:
                # Kullanıcı adı/şifre yanlışsa
                ui.show_error("Kullanıcı adı veya şifre hatalı!")
                
                # Eğer hatalı bilgi dosyadan geldiyse dosyayı silmeliyiz
                if is_from_file:
                    ui.console.print("[red]Kayıtlı bilgiler hatalı olduğu için siliniyor...[/red]")
                    ConfigManager.delete()
                
                ui.console.print("[cyan]Bilgileri tekrar girmelisiniz...[/cyan]")
                break # İç döngüyü kır -> Dış döngüye git (Bilgileri tekrar sorar)

            except Exception as e:
                # Bilinmeyen hata
                ui.show_error(f"Beklenmedik hata: {str(e)}")
                return

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nÇıkış yapıldı.")