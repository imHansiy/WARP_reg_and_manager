import sys
from PIL import Image
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("Usage: make_ico.py <input_image> <output_ico>")
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    dst.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGBA")
    sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
    # Ensure fully transparent canvas to avoid white matte
    base = Image.new("RGBA", img.size, (0,0,0,0))
    base.alpha_composite(img)
    base.save(str(dst), format="ICO", sizes=sizes)
    print(f"ICO written: {dst}")

if __name__ == "__main__":
    main()
