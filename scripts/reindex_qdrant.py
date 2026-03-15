from pathlib import Path
import sys
import os

# Proje ana dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.intake import FileScanner, ContentPreparer
from scripts.duplicate_detector import get_duplicate_detector

def reindex():
    scanner = FileScanner()
    preparer = ContentPreparer()
    detector = get_duplicate_detector()
    
    if not detector._ensure_initialized():
        print("Hata: Qdrant veya SentenceTransformers başlatılamadı. Docker'ı çalıştırdığınıza emin olun.")
        return
    
    count = 0
    eem_dir = Path("EEM")
    print("Qdrant Re-Index (Kurtarma) işlemi başlatılıyor...")
    print("-" * 50)
    
    if not eem_dir.exists():
        print("EEM klasörü bulunamadı!")
        return
        
    for file_path in eem_dir.rglob("*"):
        if file_path.is_file() and not file_path.name.startswith("."):
            try:
                # Klasör yapısından Semester ve Course bilgilerini çıkar (Örn: EEM/2024_Guz/Devre_Analizi/...)
                parts = file_path.relative_to(eem_dir).parts
                if len(parts) >= 2:
                    semester, course = parts[0], parts[1]
                else:
                    semester, course = "unknown", "unknown"
                    
                # Dosyadan sadece metni çıkar (LLM API KULLANILMIYOR!)
                scan_res = scanner.scan(str(file_path))
                prep_res = preparer.prepare(scan_res)
                
                # Qdrant'a tekrar ekle!
                if prep_res.text_content:
                    detector.add_document(
                        text=prep_res.text_content[:5000],
                        metadata={
                            "semester": semester,
                            "course": course,
                            "filename": file_path.name,
                            "path": str(file_path),
                            "material_type": "recovered" 
                        }
                    )
                    print(f"[+] Vektör Kurtarıldı: {file_path.name}")
                    count += 1
            except Exception as e:
                print(f"[X] Hata: {file_path.name} - {str(e)[:50]}")
                
    print("-" * 50)
    print(f"İŞLEM TAMAM! Toplam {count} dosya Qdrant'a başarıyla geri yüklendi.")

if __name__ == '__main__':
    reindex()
