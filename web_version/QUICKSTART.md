# Quick Start Guide - Excel Consolidator Web

## 🚀 Get Started in 3 Minutes

### Step 1: Install Dependencies (30 seconds)

```bash
cd web_version
pip install Flask openpyxl pandas xlrd werkzeug
```

Or use requirements.txt:

```bash
pip install -r requirements.txt
```

### Step 2: Run the Server (10 seconds)

```bash
python app.py
```

You should see:

```
============================================================
Excel Consolidator Web Server
============================================================
Server starting at: http://localhost:5000
Upload folder: temp_uploads
Output folder: temp_outputs
============================================================
 * Running on http://0.0.0.0:5000
```

### Step 3: Open Browser (5 seconds)

Navigate to: **http://localhost:5000**

### Step 4: Use the App (2 minutes)

1. **Drag & drop your template file** (the Excel file with formatting you want to keep)
2. **Drag & drop source files** (all the Excel files you want to consolidate)
3. **Click "Start Consolidation"**
4. **Watch progress** in real-time
5. **Download result** when complete!

## 📸 What You'll See

```
┌─────────────────────────────────────┐
│   📊 Excel Consolidator             │
│   Merge multiple Excel files        │
├─────────────────────────────────────┤
│                                     │
│ 📋 Step 1: Upload Template          │
│ ┌─────────────────────────────┐    │
│ │  Drag & drop template here   │    │
│ └─────────────────────────────┘    │
│                                     │
│ 📁 Step 2: Upload Source Files      │
│ ┌─────────────────────────────┐    │
│ │  Drag & drop Excel files     │    │
│ └─────────────────────────────┘    │
│                                     │
│ ⚙️ Settings (Optional)               │
│ ☑ Convert text to numbers           │
│ ☑ Convert percentages               │
│                                     │
│ ┌─────────────────────────────┐    │
│ │  🚀 Start Consolidation      │    │
│ └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

## 💡 Tips

### For Best Results

- **Template file**: Use your cleanest, best-formatted Excel file
- **Source files**: Should have the same structure as template
- **File names**: Avoid special characters
- **File size**: Keep under 100MB total

### Common Issues

**"Cannot start consolidation"**  
→ Make sure both template AND source files are selected

**"Processing takes too long"**  
→ Large files (50+ MB) may take 2-5 minutes

**"Download doesn't work"**  
→ Check your browser's download folder

## 🔧 Advanced Usage

### Change Server Port

Edit `app.py`:

```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Change 5000 to 8080
```

### Production Deployment

```bash
# Install Waitress
pip install waitress

# Run production server
python run_production.py
```

Serves at: http://localhost:8080

### Access from Other Devices

1. Find your computer's IP address:
   - Windows: `ipconfig` (look for IPv4)
   - Mac/Linux: `ifconfig` or `ip addr`

2. Other devices on same network can access:
   - `http://YOUR_IP:5000`
   - Example: `http://192.168.1.100:5000`

## 📊 Example Files

### Template File Structure

```
A1: School Name    B1: Student Count    C1: Budget
A2: [School 1]     B2: [Number]         C2: [Amount]
A3: [School 2]     B3: [Number]         C3: [Amount]
```

### Source Files

Each source file should have:
- Same columns (A, B, C...)
- Same rows (1, 2, 3...)
- Numbers to be summed in corresponding cells

### Result

The consolidated file will have:
- Template's formatting preserved
- All numbers summed cell-by-cell
- Comments showing which files contributed
- Orange borders on consolidated cells

## 🎓 How It Works

1. **You upload** → Files saved to `temp_uploads/`
2. **Server processes** → Background thread consolidates
3. **You track progress** → JavaScript polls status every second
4. **Result ready** → Saved to `temp_outputs/`
5. **You download** → File sent to browser
6. **Auto-cleanup** → Old files deleted after 1 hour

## 🆘 Need Help?

Check these files:
- `README.md` - Full documentation
- `app.py` - Flask server code
- `services/consolidator.py` - Core consolidation logic

## 🎯 Next Steps

- ✅ You have a working web version!
- ✅ Share the link with colleagues
- ✅ Deploy to cloud (Heroku, Railway, Render)
- ✅ Add authentication if needed

Enjoy your web-based Excel Consolidator! 🎉
