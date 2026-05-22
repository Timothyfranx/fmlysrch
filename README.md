# 🚀 FamilySearch Power Tool Pro — Beginner's Guide

This tool is a high-performance automation assistant designed to help you fill out FamilySearch Oral Genealogy pedigree forms quickly and accurately. It includes a built-in editor to fix your data before pushing it to the website.

---

## 📋 Table of Contents
1. [Prerequisites](#-prerequisites)
2. [Installation (Step-by-Step)](#-installation-step-by-step)
3. [Configuration](#-configuration)
4. [How to Use the App](#-how-to-use-the-app)
5. [JSON Utility Tools (Fixing Broken Data)](#-json-utility-tools-fixing-broken-data)
6. [Security & Troubleshooting](#-security--troubleshooting)

---

## 🛠 Prerequisites
Before you start, make sure you have the following installed on your computer:
- **Python 3.12 or higher**: Download it from [python.org](https://www.python.org/downloads/). 
  - *Crucial for Windows Users*: When installing, check the box that says **"Add Python to PATH"**.
- **Internet Connection**: Required for the initial setup and to access FamilySearch.

---

## 🚀 Installation (Step-by-Step)

### 1. Open your Terminal or Command Prompt
- **Windows**: Search for `cmd` or `PowerShell` in the Start menu.
- **Mac/Linux**: Open the `Terminal` app.

### 2. Navigate to the project folder
Use the `cd` command to move into the folder where you downloaded this tool:
```bash
cd path/to/this/folder
```

### 3. Create a Virtual Environment (Highly Recommended)
This keeps the tool's files separate from the rest of your computer.
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install the requirements
Run this command to install all the necessary "brain" components for the tool:
```bash
pip install -r requirements.txt
```

### 5. Install the Browser Driver
The tool uses a special version of Chrome to fill the forms. Install it with:
```bash
playwright install chromium
```

---

## ⚙️ Configuration

Your settings are stored in `config.json`. 
- **⚠️ IMPORTANT**: Do **NOT** share your `config.json` with anyone if you are uploading this code to GitHub. It contains your FamilySearch password in plain text.
- The tool will automatically create this file for you the first time you enter your login details in the app.

---

## 📖 How to Use the App

### 1. Prepare your JSON Data
- Each form has a 4-digit ID at the end of its URL (e.g., `https://.../0727`).
- Name your data file to match that ID (e.g., `0727.json`).
- Place all `.json` files in the same folder as `app.py`.

### 2. Launch the App
```bash
# Windows
python app.py

# Mac/Linux
python3 app.py
```

### 3. Load Data & Start Filling
1. **Automation Tab**: Paste your FamilySearch URLs into the big text box (one per line).
2. **Login**: Enter your FamilySearch username and password.
3. **Sync**: Click **"🔄 SYNC"**. This connects your URLs to your JSON files.
4. **Nitro Fill**: Click **"🚀 START NITRO FILL"**. A browser will open and start typing for you!

---

## 🛠 JSON Utility Tools (Fixing & Aligning Data)

If you have a JSON file that has syntax errors or needs formatting, or you want to align pedigree death places, we have included powerful scripts to help:

### 1. Repair Broken JSON (`json_repair.py`)
If your JSON file has extra brackets, missing commas, or was copied incorrectly, run this to surgically recover the data:
```bash
python3 json_repair.py 0727.json
```

### 2. Format/Clean JSON (`json_formatter.py`)
If your JSON is valid but looks messy and hard to read, run this to make it pretty and sorted:
```bash
python3 json_formatter.py 0727.json
```

### 3. Align Death Places (`death_place_to_birth_place.py`)
For deceased records (where `living` is `"No"`), this script copies the `birth_location` directly to the `death_location` field so that they are perfectly aligned:
```bash
python3 death_place_to_birth_place.py 0727.json
```

---

## 🔍 Interactive Table Zoom Control

To view all genealogy data fields simultaneously on any screen size, you can zoom the data table in and out:
- **Visual Buttons**: Use the `➖`, `🔄`, and `➕` buttons in the **TABLE ZOOM** section of the sidebar to dynamically change scale.
- **Keyboard Shortcuts**:
  - `Ctrl` + `+` or `Ctrl` + `=` to Zoom In
  - `Ctrl` + `-` to Zoom Out
  - `Ctrl` + `0` to Reset Zoom to 100%
- **Mouse Scroll**: Hold `Ctrl` and scroll your mouse wheel over the table to zoom dynamically.

---


## ⚠️ Security & Troubleshooting

- **"ModuleNotFoundError"**: This means you skipped Step 4 of the installation. Run `pip install -r requirements.txt`.
- **"Playwright not found"**: This means you skipped Step 5. Run `playwright install chromium`.
- **Login Blocks**: If FamilySearch blocks you with a "security check," simply solve the puzzle in the automated browser window, and the script will continue automatically.
- **Privacy**: I have updated the `.gitignore` file so that your `config.json` (with your password) will **NEVER** be pushed to GitHub accidentally.
