import os
import struct

dir_path = 'docs/screenshots'
files = sorted(os.listdir(dir_path))
print(f"Total valid screenshots in {dir_path}: {len(files)}")
print("-" * 80)
print(f"{'Filename':<45} | {'Dimensions':<10} | {'Size (KB)':<10}")
print("-" * 80)

for f in files:
    fp = os.path.join(dir_path, f)
    size = os.path.getsize(fp)
    with open(fp, 'rb') as img:
        header = img.read(24)
        if header.startswith(b'\x89PNG\r\n\x1a\n'):
            w, h = struct.unpack('>II', header[16:24])
            dim = f"{w}x{h}"
        else:
            dim = "NOT_PNG"
    print(f"{f:<45} | {dim:<10} | {size/1024:>9.1f}")
