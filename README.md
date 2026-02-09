# 🧠 Smart Summarizer

An AI-powered document summarization tool with multi-language support, audio/video generation, mind mapping, and intelligent Q&A capabilities.

## ✨ Features

- 📄 **Multi-Format Support**: PDF, DOCX, TXT, MD, Images, Websites, YouTube videos
- 🌍 **10 Languages**: English, Spanish, French, German, Chinese, Japanese, Russian, Arabic, Hindi, Portuguese
- 🎧 **Audio Overview**: Convert summaries to speech (MP3)
- 🎬 **Video Overview**: Generate visual presentations with key points
- 🗺️ **Mind Map**: Create hierarchical mind maps from content
- 📊 **Reports**: Generate structured reports with download options
- 💬 **AI Q&A**: Ask questions about your documents
- 🔄 **Dynamic Translation**: Change language anytime to re-translate everything
- ⚡ **Fast Processing**: Optimized with Groq API for quick responses

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/smart-summarizer.git
cd smart-summarizer
```

2. **Create virtual environment**
```bash
python -m venv venv
```

3. **Activate virtual environment**
- Windows:
```bash
venv\Scripts\activate
```
- Mac/Linux:
```bash
source venv/bin/activate
```

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

5. **Set up environment variables**

Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

**Get API Keys:**
- Groq API: https://console.groq.com/keys (Recommended for speed)
- Gemini API: https://makersuite.google.com/app/apikey (Optional fallback)

6. **Run the application**
```bash
python app.py
```

7. **Open in browser**
```
http://localhost:5000
```

## 📖 Usage

1. **Upload Document**: Click "Add" or "Upload a source"
2. **Select Language**: Choose from 10 supported languages
3. **Get Summary**: Automatic AI-powered summarization
4. **Studio Features**:
   - Click **Audio Overview** to generate speech
   - Click **Video Overview** to create visual presentation
   - Click **Mind Map** to generate concept map
   - Click **Reports** to create structured document
5. **Ask Questions**: Use the search box to ask about your document
6. **Change Language**: Switch language anytime to re-translate

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **AI Models**: Groq (Llama 3.1), Google Gemini
- **Text-to-Speech**: gTTS
- **Visualization**: Matplotlib, NetworkX
- **PDF Processing**: PyPDF2
- **Document Processing**: python-docx
- **OCR**: Tesseract (pytesseract)
- **Web Scraping**: BeautifulSoup4
- **YouTube**: yt-dlp, youtube-transcript-api

## 📁 Project Structure

```
smart-summarizer/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── .gitignore            # Git ignore rules
├── static/
│   └── style.css         # Styling
├── templates/
│   ├── index.html        # Landing page
│   └── next.html         # Main application
└── Uploads/              # Temporary file storage
```

## ⚙️ Configuration

### Supported File Types
- Documents: PDF, DOCX, TXT, MD
- Images: JPG, JPEG, PNG (with OCR)
- Web: URLs, YouTube videos
- Text: Direct paste

### Language Codes
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `zh` - Chinese
- `ja` - Japanese
- `ru` - Russian
- `ar` - Arabic
- `hi` - Hindi
- `pt` - Portuguese

## 🔧 Troubleshooting

**Issue**: "No module named 'flask'"
- **Solution**: Make sure virtual environment is activated and run `pip install -r requirements.txt`

**Issue**: Audio generation fails
- **Solution**: Check internet connection (gTTS requires internet)

**Issue**: OCR not working
- **Solution**: Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract

**Issue**: Slow responses
- **Solution**: Make sure GROQ_API_KEY is configured in .env file

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Groq for fast AI inference
- Google Gemini for AI capabilities
- Flask community
- Open source contributors

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

Made with ❤️ by [Your Name]
