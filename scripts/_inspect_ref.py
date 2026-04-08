import re, base64
from io import BytesIO

with open('Gage type 1.htm', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

imgs = re.findall(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', html)
print(f'Found {len(imgs)} embedded images')

if imgs:
    from PIL import Image
    imgdata = base64.b64decode(imgs[0])
    img = Image.open(BytesIO(imgdata))
    print(f'First image size: {img.size}')
    img.save('minitab_ref_chart1.png')
    print('Saved minitab_ref_chart1.png')
