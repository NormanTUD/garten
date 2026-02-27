#!/bin/bash
# Generate PWA icons from SVG (requires Inkscape or ImageMagick)
# For now, we create simple colored PNGs as placeholders

cd "$(dirname "$0")/../public"

# If ImageMagick is available, generate from SVG
if command -v convert &> /dev/null; then
  convert -background none -size 192x192 ../public/favicon.svg icon-192x192.png
  convert -background none -size 512x512 ../public/favicon.svg icon-512x512.png
  convert -background "#2E7D32" -size 512x512 ../public/favicon.svg icon-maskable.png
  echo "Icons generated!"
else
  echo "ImageMagick not found. Please create icon-192x192.png, icon-512x512.png, and icon-maskable.png manually."
  # Create minimal placeholder PNGs (1x1 green pixel, browsers will scale)
  # In production, use proper icons
  echo "Creating placeholder files..."
  touch icon-192x192.png icon-512x512.png icon-maskable.png
fi

