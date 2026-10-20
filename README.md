# Grvty

A private photo grading app for Windows. Describe a look ("moody black and white, warm sepia highlights"), choose how many versions to see, pick a favourite, fine-tune it, save it as a Lightroom preset, and export a whole batch with the same look. Everything runs on your own laptop.

## Install

Download **GrvtySetup.exe** from the [latest build](../../releases/tag/grvty-latest), double-click it and press **Install**.

## Run from source

```
pip install -r requirements.txt
python app.py
```

## What's inside

- `grvty/engine.py`: the grading engine (exposure, tone, colour mixer, black & white, colour grading, curve, vignette, grain)
- `grvty/looks.py`: turns words into looks and makes variations; remembers which looks you pick
- `grvty/xmp.py`: writes Lightroom presets
- `grvty/server.py`: the local server the window talks to
- `ui/`: the window (liquid glass, Cute and Dark themes)
- `installer/`: Grvty Setup, the one-button installer
