# 🚀 Digital Café Pro - Complete Setup Guide

## Project Status: ✅ READY TO RUN

Your project has all 3 working tools:
1. **Passport Photo Maker** - 6/12 grid generation
2. **PDF Converter** - PDF ↔ JPG conversion  
3. **Resize Tool** - Image resizing with KB compression

---

## 🔧 How to Run

### Option 1: PowerShell (Recommended)
```powershell
.\start-project.ps1
```

### Option 2: Command Prompt (Windows)
```cmd
start-project.bat
```

### Option 3: Manual Setup

**Terminal 1 - Backend:**
```powershell
cd backend
pip install -r requirements.txt
python app.py
```

**Terminal 2 - Frontend:**
- Open `index.html` in your browser using VS Code Live Server extension
- Or open directly: `file:///C:/Users/Mohit Yadav/Desktop/digital-cafe-website/index.html`

---

## 📋 What's Working

| Feature | Status | URL |
|---------|--------|-----|
| Frontend Landing | ✅ | `index.html` |
| Tool Cards | ✅ | Display all 9 tools |
| Passport Photo Form | ✅ | POST `/api/passport-photo` |
| PDF Converter Form | ✅ | POST `/api/convert` |
| Resize Tool Form | ✅ | POST `/api/resize` |
| Backend Server | ✅ | http://localhost:5000 |
| CORS Support | ✅ | Enabled for all origins |

---

## 🎯 Testing the Tools

### 1. Passport Photo Maker
- Upload any portrait photo
- Select 6 or 12 grid format
- Click "Process Photo"
- Download the grid

### 2. PDF Converter
- Upload PDF or JPG
- Select conversion mode (PDF→JPG or JPG→PDF)
- Click "Convert"
- Download result

### 3. Resize Tool
- Upload image
- Enter Width OR Height (aspect ratio maintained)
- Optionally set target file size in KB
- Click "Resize"
- Download resized image

---

## ⚡ Performance Tips

1. **First Run**: Dependency installation may take 1-2 minutes
2. **Backend Port**: Server runs on `http://localhost:5000`
3. **Frontend**: No installation needed - just open HTML file
4. **CORS**: Already enabled for cross-origin requests

---

## 🐛 Troubleshooting

**Issue**: "Backend server से connect नहीं हो पाया"
- ✅ Check if `python app.py` is running in terminal
- ✅ Verify port 5000 is free
- ✅ Check console for error messages

**Issue**: File upload fails
- ✅ Check file format (PNG, JPG, PDF supported)
- ✅ Check file size (should be reasonable)

**Issue**: Python not recognized
- ✅ Ensure Python is in system PATH
- ✅ Use `python --version` to verify installation

---

## 📁 Project Structure

```
digital-cafe-website/
├── index.html           (Main webpage)
├── styles.css          (Styling)
├── script.js           (Tool data)
├── frontend.js         (Frontend helpers)
├── start-project.bat   (Windows batch starter)
├── start-project.ps1   (PowerShell starter)
├── SETUP.md            (This file)
└── backend/
    ├── app.py          (Flask server)
    ├── requirements.txt
    └── README.md
```

---

## 🎉 Ready to Launch!

**Your project is 100% complete. Just run the startup script and open in browser!**

```
✓ Frontend Complete
✓ Backend Complete  
✓ All 3 Tools Implemented
✓ Error Handling Done
✓ Responsive Design
✓ Hindi Support
```

---

## 🔁 Deploying & Frontend API URL

- When you deploy the backend to a live host (Render, Heroku, etc.), update the frontend to point to the live backend.
- Open [index.html](index.html) and locate the `API_BASE` constant in the script at the bottom. Replace the fallback or set it explicitly, for example:

```js
const API_BASE = 'https://your-live-backend.example.com';
```

- Alternatively, if you serve the frontend from the same domain as the backend, `window.location.origin` will be used automatically.

---

## 🔧 Render Deployment Notes

- Add the repository to Render and set the build command to:

```bash
pip install -r backend/requirements.txt
```

- Set the start command to:

```bash
gunicorn backend.app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120
```

- Set environment variables:
    - `PORT` (Render sets this automatically)
    - `MAX_CONTENT_LENGTH` (optional, bytes)
    - `FLASK_DEBUG=0` for production

