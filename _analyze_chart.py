"""Analyze the Minitab reference chart layout by examining pixel regions."""
import re, base64
from io import BytesIO
from PIL import Image
import numpy as np

with open('Gage type 1.htm', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

imgs = re.findall(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', html)
imgdata = base64.b64decode(imgs[0])
img = Image.open(BytesIO(imgdata))
arr = np.array(img)

print(f"Image shape: {arr.shape}")  # (height, width, channels)
print(f"Image size: {img.size}")    # (width, height)

# Check color distribution in different quadrants to understand layout
h, w = arr.shape[:2]
mid_h, mid_w = h // 2, w // 2

# Sample some key locations to understand what's where
# Look at the vertical center strip (y-axis area) of the left panel
for label, region in [
    ("Top-Left quarter", arr[:mid_h, :mid_w]),
    ("Top-Right quarter", arr[:mid_h, mid_w:]),
    ("Bottom-Left quarter", arr[mid_h:, :mid_w]),
    ("Bottom-Right quarter", arr[mid_h:, mid_w:]),
]:
    mean_color = region.mean(axis=(0,1))
    print(f"{label}: mean RGB = {mean_color[:3].astype(int)}")

# Look for the boundary between the two chart panels
# Scan vertical line in middle area for mostly-white columns
print("\nScanning for panel boundary (white columns):")
for x in range(w//3, 2*w//3, 10):
    col = arr[30:h-30, x, :3]
    white_frac = (col.mean(axis=1) > 240).mean()
    if white_frac > 0.8:
        print(f"  ~white column at x={x} ({white_frac:.0%} white)")

# Also extract text regions by looking for dark pixels on light background
# Look at top strip for title text
title_strip = arr[:30, :, :3]
print(f"\nTitle strip mean RGB: {title_strip.mean(axis=(0,1)).astype(int)}")

# Check if there's a distinct right panel (histogram)
print(f"\n=== Layout analysis ===")
right_third = arr[30:h-60, 2*w//3:, :3]
left_two_thirds = arr[30:h-60, :2*w//3, :3]
print(f"Left 2/3 mean: {left_two_thirds.mean(axis=(0,1)).astype(int)}")
print(f"Right 1/3 mean: {right_third.mean(axis=(0,1)).astype(int)}")

# Check for blue bars (histogram) in right portion - look for blue-ish pixels
blue_mask = (arr[:,:,2] > 150) & (arr[:,:,0] < 100) & (arr[:,:,1] < 100)
blue_coords = np.where(blue_mask)
if len(blue_coords[0]) > 0:
    print(f"\nBlue pixels found: {len(blue_coords[0])}")
    print(f"  Y range: {blue_coords[0].min()} - {blue_coords[0].max()}")
    print(f"  X range: {blue_coords[1].min()} - {blue_coords[1].max()}")
    blue_x_center = blue_coords[1].mean()
    print(f"  X center of blue region: {blue_x_center:.0f} (image width: {w})")
    if blue_x_center > mid_w:
        print("  -> Blue bars are in RIGHT half (histogram right of run chart)")
    else:
        print("  -> Blue bars are in LEFT half")
else:
    print("\nNo blue pixels found - trying other color ranges...")
    # Try lighter blue
    lb_mask = (arr[:,:,2] > 100) & (arr[:,:,0] < 150) & (arr[:,:,1] < 150) & (arr[:,:,2] > arr[:,:,0])
    lb_coords = np.where(lb_mask)
    if len(lb_coords[0]) > 0:
        print(f"Light blue pixels: {len(lb_coords[0])}")
        print(f"  X range: {lb_coords[1].min()} - {lb_coords[1].max()}")

# Look for red/green lines (reference lines)
red_mask = (arr[:,:,0] > 180) & (arr[:,:,1] < 80) & (arr[:,:,2] < 80)
green_mask = (arr[:,:,1] > 120) & (arr[:,:,0] < 80) & (arr[:,:,2] < 80)
red_coords = np.where(red_mask)
green_coords = np.where(green_mask)
if len(red_coords[0]) > 0:
    print(f"\nRed pixels: Y={red_coords[0].min()}-{red_coords[0].max()}, X={red_coords[1].min()}-{red_coords[1].max()}")
if len(green_coords[0]) > 0:
    print(f"Green pixels: Y={green_coords[0].min()}-{green_coords[0].max()}, X={green_coords[1].min()}-{green_coords[1].max()}")

# Count unique colors to see what the palette is
print("\nTop 10 most common pixel colors:")
pixels = arr.reshape(-1, arr.shape[2])[:, :3]  # Just RGB
unique, counts = np.unique(pixels, axis=0, return_counts=True)
top_idx = counts.argsort()[-10:][::-1]
for idx in top_idx:
    print(f"  RGB({unique[idx][0]:3d},{unique[idx][1]:3d},{unique[idx][2]:3d}): {counts[idx]}")
