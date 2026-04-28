# FamilySearch Power Tool Pro — Setup & User Guide

A high-performance automation tool for bulk-populating FamilySearch Oral Genealogy pedigree forms with built-in data editing and multi-form support.

---

## ⚡ Key Features
- **Turbo Fill Mode**: High-speed data entry with automated login and page navigation.
- **Multi-Form Automation**: Paste multiple URLs to process them sequentially in separate tabs.
- **Built-in Data Editor**: A full table view of your JSON data with search and filtering.
- **Bulk Editing**: Select multiple rows to update family names or locations all at once.
- **Auto-Matching**: Automatically matches form URLs to JSON files based on the 4-digit ID (e.g., `1205.json` for a URL ending in `1205`).

---

## 🛠️ One-Time Setup

### 1. Install Dependencies
Ensure you are using the virtual environment:

**Windows:**
```bash
.\venv\Scripts\activate
pip install -r requirements.txt
```

**Linux/macOS:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Playwright Browsers
```bash
playwright install chromium
```

---

## 🚀 Running the App

Run the application using the virtual environment:

**Windows:**
```bash
.\venv\Scripts\python.exe app.py
```

**Linux/macOS:**
```bash
./venv/bin/python app.py
```

---

## 📖 How to Use

### Step 1: Prepare Your Data
- Name your JSON data files using the 4-digit ID found at the end of your FamilySearch form URLs (e.g., `1205.json`, `002.json`).
- Place these files in the same directory as `app.py`.

### Step 2: Load and Sync
1. Open the app and paste your **Form URLs** into the text box (one per line).
2. Enter your FamilySearch **Username** and **Password**.
3. Click **"🔄 STEP 1: LOAD & SYNC DATA"**.
4. The app will verify your JSON files exist and populate the **Data Editor** tab.

### Step 3: Review and Edit (Optional)
1. Switch to the **"Data Editor"** tab.
2. Use the **Search** box to find specific people or families.
3. **Double-click** any cell to edit data manually.
4. **Bulk Edit**: Select multiple rows (Ctrl/Shift + Click), click "Bulk Edit", choose a column, and apply a value to all selected rows.
5. Click **"Save Changes to File"** if you want to update your JSON files permanently.

### Step 4: Start Automation
1. Go back to the **"Automation"** tab.
2. Click **"🚀 STEP 2: START TURBO FILL"**.
3. A browser window will open. The script will log in and begin filling each form one by one.
4. **DO NOT** close the browser. Once finished, the status will show "Done!", and you can review the work before manually closing the browser.

---

## ⚠️ Safety Notes
- **Login Security**: Your credentials are saved locally in `config.json` for convenience. They are never sent to any server other than FamilySearch.
- **Browser Lock**: If the browser fails to open, ensure no other instance of the app is running and try again.
- **Error 15**: If the website blocks the browser, wait a few minutes or try logging in manually in the window that appears.
