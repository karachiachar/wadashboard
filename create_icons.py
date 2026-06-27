import os
from PIL import Image, ImageDraw

def create_icon(size, filename):
    img = Image.new('RGB', (size, size), color='#128c7e')
    d = ImageDraw.Draw(img)
    margin = size // 5
    d.ellipse((margin, margin, size-margin, size-margin), fill='#00a884', outline='white', width=size//25)
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename)

if __name__ == "__main__":
    create_icon(192, 'static/icons/icon-192x192.png')
    create_icon(512, 'static/icons/icon-512x512.png')
    print("Icons created successfully.")
