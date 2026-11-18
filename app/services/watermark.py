import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from app.config import settings

def apply_watermark(image_path: Path, output_path: Path, text: str = "GIGLY PROTECTED PREVIEW • PAGO PENDIENTE"):
    """
    Applies a semi-transparent repeating diagonal watermark across the image.
    This protects the seller's work before the buyer approves delivery and releases escrow.
    """
    try:
        with Image.open(image_path) as base_image:
            base_image = base_image.convert("RGBA")
            width, height = base_image.size

            # Create a transparent overlay for text
            watermark_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark_layer)

            # Try to load a nice font, or fallback to default
            font_size = max(24, int(min(width, height) / 18))
            try:
                # Common Windows fonts or fallback
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", font_size)
                except Exception:
                    font = ImageFont.load_default()

            # Diagonal text watermark stamp
            # Semi-transparent turquoise and white accents
            stamp_text = f"🛡️ {text} 🛡️"
            
            # Step spacing
            step_x = int(font_size * 14)
            step_y = int(font_size * 5)
            
            for y in range(-height, height * 2, step_y):
                for x in range(-width, width * 2, step_x):
                    # Draw subtle shadow
                    draw.text((x + 2, y + 2), stamp_text, font=font, fill=(0, 0, 0, 70))
                    # Draw main text in bold turquoise/white
                    draw.text((x, y), stamp_text, font=font, fill=(20, 184, 166, 110))

            # Center prominent banner
            banner_height = int(font_size * 2.5)
            banner_y = (height - banner_height) // 2
            # Dark transparent background bar
            draw.rectangle([(0, banner_y), (width, banner_y + banner_height)], fill=(18, 20, 23, 190))
            
            center_label = "🔒 VISTA PREVIA PROTEGIDA POR GIGLY • APROBAR PARA DESCARGAR ORIGINAL"
            draw.text(((width - len(center_label) * (font_size * 0.45)) // 2, banner_y + int(font_size * 0.6)), 
                      center_label, font=font, fill=(234, 236, 239, 230))

            # Rotate overlay slightly for anti-theft diagonal effect
            # Composite images
            watermarked = Image.alpha_composite(base_image, watermark_layer)
            
            # Save as RGB JPEG or PNG
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.suffix.lower() in [".jpg", ".jpeg"]:
                watermarked.convert("RGB").save(output_path, "JPEG", quality=85)
            else:
                watermarked.save(output_path, "PNG")

        return True
    except Exception as e:
        print(f"Error applying watermark: {e}")
        return False

def generate_non_image_preview(output_path: Path, filename: str):
    """
    Generates a protected visual banner preview for non-image deliverable files (e.g. ZIP, PDF, CODE).
    """
    try:
        width, height = 800, 450
        img = Image.new("RGBA", (width, height), (26, 29, 36, 255))
        draw = ImageDraw.Draw(img)
        
        font_large = ImageFont.load_default()
        
        # Border
        draw.rectangle([(10, 10), (width - 10, height - 10)], outline=(20, 184, 166, 255), width=3)
        
        # Text
        draw.text((width // 4, height // 3), f"📁 Archivo Entregable Protegido", fill=(234, 236, 239, 255), font=font_large)
        draw.text((width // 4, height // 2), f"Archivo: {filename}", fill=(20, 184, 166, 255), font=font_large)
        draw.text((width // 4, int(height * 0.65)), "Acepta la entrega para desbloquear la descarga directa.", fill=(176, 181, 189, 255), font=font_large)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(output_path, "JPEG", quality=85)
        return True
    except Exception as e:
        print(f"Error generating non-image preview: {e}")
        return False
