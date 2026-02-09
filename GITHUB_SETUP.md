# 📤 How to Push to GitHub

Follow these steps to upload your Smart Summarizer project to GitHub:

## Step 1: Create GitHub Repository

1. Go to https://github.com
2. Click the **"+"** icon in top right → **"New repository"**
3. Fill in:
   - **Repository name**: `smart-summarizer`
   - **Description**: "AI-powered document summarizer with multi-language support"
   - **Visibility**: Choose Public or Private
   - **DO NOT** check "Initialize with README" (we already have one)
4. Click **"Create repository"**

## Step 2: Initialize Git (if not already done)

Open terminal in your project folder and run:

```bash
git init
```

## Step 3: Add Files to Git

```bash
git add .
```

This adds all files except those in `.gitignore`

## Step 4: Commit Files

```bash
git commit -m "Initial commit: Smart Summarizer with AI features"
```

## Step 5: Connect to GitHub

Replace `YOUR_USERNAME` with your GitHub username:

```bash
git remote add origin https://github.com/YOUR_USERNAME/smart-summarizer.git
```

## Step 6: Push to GitHub

```bash
git branch -M main
git push -u origin main
```

If prompted, enter your GitHub credentials.

## Step 7: Verify

Go to your GitHub repository URL:
```
https://github.com/YOUR_USERNAME/smart-summarizer
```

You should see all your files!

---

## 🔄 Future Updates

When you make changes to your code:

```bash
# 1. Add changed files
git add .

# 2. Commit with message
git commit -m "Description of changes"

# 3. Push to GitHub
git push
```

---

## 🔐 Important Security Notes

✅ **What's Protected:**
- `.env` file (contains API keys) - NOT uploaded to GitHub
- `venv/` folder - NOT uploaded
- `Uploads/` folder contents - NOT uploaded
- `.vscode/` settings - NOT uploaded

✅ **What's Included:**
- All source code (`app.py`, templates, static files)
- `requirements.txt` (dependencies list)
- `README.md` (documentation)
- `.env.example` (template for users)
- `.gitignore` (protection rules)

---

## 📝 Before Sharing

1. **Update README.md**:
   - Replace `[Your Name]` with your actual name
   - Replace `YOUR_USERNAME` with your GitHub username
   - Add screenshots if you want

2. **Test the setup**:
   - Clone your repo in a different folder
   - Follow the README instructions
   - Make sure everything works

3. **Add screenshots** (optional):
   - Create a `screenshots/` folder
   - Add images of your app
   - Reference them in README.md

---

## 🎉 You're Done!

Your project is now on GitHub and ready to share with the world!

Share your repository link:
```
https://github.com/YOUR_USERNAME/smart-summarizer
```
