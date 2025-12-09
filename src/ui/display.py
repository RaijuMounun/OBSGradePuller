from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from typing import List, Optional
from src.models import CourseGrade, ExamStats

class DisplayManager:
    def __init__(self):
        self.console = Console()

    def print_banner(self):
        self.console.clear()
        self.console.print(Panel(
            "[bold cyan]🎓 OBS Grade Puller v3.0[/bold cyan]",
            style="bold white",
            border_style="cyan"
        ))

    def show_message(self, msg: str, style: str = "green"):
        self.console.print(f"[{style}]{msg}[/{style}]")

    def ask_input(self, prompt: str, password: bool = False) -> str:
        return self.console.input(f"[bold yellow]{prompt}: [/bold yellow]", password=password)

    def ask_choice(self, prompt: str, choices: List[str]) -> str:
        """Kullanıcıya seçenekler sunar ve seçimini döndürür."""
        self.console.print(f"\n[bold cyan]{prompt}[/bold cyan]")
        for idx, choice in enumerate(choices, 1):
            self.console.print(f"  [green]{idx}.[/green] {choice}")
        
        while True:
            selection = self.console.input("[bold yellow]Seçiminiz (No): [/bold yellow]")
            if selection.isdigit() and 1 <= int(selection) <= len(choices):
                return choices[int(selection) - 1]
            self.console.print("[red]Geçersiz seçim, tekrar deneyin.[/red]")

    def _format_score(self, my_score: str, class_avg: str) -> str:
        """Notu renklendirir ve ortalamaya göre ok işareti ekler."""
        if not my_score.replace(',', '').isdigit(): 
            return my_score # Girmediyse veya tire ise olduğu gibi dön

        score_val = float(my_score.replace(',', '.'))
        
        # Renklendirme
        color = "white"
        if score_val < 50: color = "red"
        elif score_val >= 85: color = "green"
        elif score_val >= 70: color = "cyan"
        
        # Ortalama Kıyaslaması
        icon = ""
        if class_avg.replace(',', '').replace('.', '').isdigit():
            avg_val = float(class_avg.replace(',', '.'))
            if score_val > avg_val: icon = "[bold green]↑[/bold green]"
            elif score_val < avg_val: icon = "[bold red]↓[/bold red]"
        
        return f"[{color}]{my_score}[/{color}] {icon}"

    def render_grades(self, grades: List[CourseGrade], term_name: str):
        if not grades:
            self.console.print("[yellow]Gösterilecek not bulunamadı.[/yellow]")
            return

        table = Table(
            title=f"Not Durumu ({term_name})", 
            box=box.ROUNDED, 
            header_style="bold magenta",
            show_lines=True
        )

        # Sütunları Tanımla
        table.add_column("Ders", style="cyan", no_wrap=True)
        
        # Vize Grubu
        table.add_column("Vize", justify="center")
        table.add_column("Ort.", justify="center", style="dim")
        
        # Final Grubu
        table.add_column("Final", justify="center")
        table.add_column("Ort.", justify="center", style="dim")
        
        # Büt Grubu
        table.add_column("Büt", justify="center")
        table.add_column("Ort.", justify="center", style="dim")
        
        table.add_column("Harf", justify="center", style="bold white")

        for g in grades:
            # Notları formatla
            v_str = self._format_score(g.midterm.score, g.midterm.class_avg)
            f_str = self._format_score(g.final.score, g.final.class_avg)
            b_str = self._format_score(g.makeup.score, g.makeup.class_avg)

            # Harf notu renklendirmesi (FF ise kırmızı)
            letter = g.letter_grade
            if letter.startswith("F") or letter in ["DZ", "YZ"]:
                letter = f"[bold red]{letter}[/bold red]"
            else:
                letter = f"[bold green]{letter}[/bold green]"

            table.add_row(
                g.name,
                v_str, g.midterm.class_avg,
                f_str, g.final.class_avg,
                b_str, g.makeup.class_avg,
                letter
            )

        self.console.print(table)