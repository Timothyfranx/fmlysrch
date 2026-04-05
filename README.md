# FamilySearch AutoFill — Setup Guide

## One-time Setup

### 1. Install dependencies
Open terminal in this folder and run:

```
pip install -r requirements.txt
```

### 2. Install Tesseract OCR (for Windows)
Download and install from:
https://github.com/UB-Mannheim/tesseract/wiki

After installing, add it to PATH or set the path in app.py:
- Open app.py
- Add this line near the top (after imports):
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

### 3. Install Playwright browsers
```
playwright install chromium
```

---

## Running the App

```
python app.py
```

---

## How to Use

1. Enter your FamilySearch **username and password** → click "Save Login"
2. Paste the **form URL** (e.g. https://www.familysearch.org/en/oral-gen/pedigree-form/NG35_002_...)
3. Click **Upload Photo** → select your paper sheet photo
4. Click **Run OCR** → wait for rows to appear in the table
5. **Double-click** any cell to fix OCR mistakes
6. Click **▶ Fill FamilySearch** → browser opens and fills everything automatically

---

## Notes
- Your login is saved locally in config.json (never sent anywhere)
- The browser window stays open so you can review before the site auto-saves
- If OCR misses rows, you can manually add them (edit the table directly)
