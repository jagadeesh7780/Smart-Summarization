from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import shutil
import pytesseract
from PIL import Image
import PyPDF2
import docx
# import speech_recognition as sr
# from pydub import AudioSegment
import logging
import io
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import google.generativeai as genai
import time
import networkx as nx
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
from gtts import gTTS
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import base64
from dotenv import load_dotenv
import glob
from datetime import datetime, timedelta
from groq import Groq

load_dotenv()
if os.getenv('GEMINI_API_KEY'):
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'Uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists('static'):
    os.makedirs('static')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cleanup old files in static folder
def cleanup_old_files():
    try:
        # Delete files older than 1 hour
        cutoff_time = datetime.now() - timedelta(hours=1)
        patterns = ['static/audio_*.mp3', 'static/video_*.png', 'static/mindmap_*.png', 'static/report_*.pdf', 'static/summary_*.*']
        
        for pattern in patterns:
            for filepath in glob.glob(pattern):
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        logger.info(f"Cleaned up old file: {filepath}")
                except Exception as e:
                    logger.error(f"Error deleting {filepath}: {e}")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

# Run cleanup on startup
cleanup_old_files()

SUPPORTED_LANGUAGES = {'en', 'es', 'fr', 'de', 'zh-cn', 'ja', 'ru', 'ar', 'hi', 'pt'}

pytesseract.pytesseract.tesseract_cmd = shutil.which('tesseract') or r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_file(file_path, file_type, language='en'):
    try:
        if file_type == 'pdf':
            try:
                with open(file_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    if len(pdf.pages) == 0:
                        logger.error(f"PDF file {file_path} is empty")
                        return ''
                    text = ''
                    for page in pdf.pages:
                        extracted = page.extract_text() or ''
                        text += extracted
                    if not text.strip():
                        logger.error(f"No text extracted from PDF {file_path}")
                        return ''
                    return text
            except PyPDF2.errors.PdfReadError as e:
                logger.error(f"PDF read error for {file_path}: {e}")
                return ''
            except Exception as e:
                logger.error(f"Unexpected error processing PDF {file_path}: {e}")
                return ''
        elif file_type in ['txt', 'text', 'md', 'markdown']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                if not text.strip():
                    logger.error(f"No text in file {file_path}")
                    return ''
                return text
            except Exception as e:
                logger.error(f"Error reading text file {file_path}: {e}")
                return ''
        elif file_type == 'docx':
            try:
                doc = docx.Document(file_path)
                text = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
                if not text:
                    logger.error(f"No text extracted from DOCX {file_path}")
                    return ''
                return text
            except Exception as e:
                logger.error(f"Error processing DOCX {file_path}: {e}")
                return ''
        elif file_type in ['jpg', 'jpeg', 'png']:
            try:
                image = Image.open(file_path)
                text = pytesseract.image_to_string(image, lang=language)
                if not text.strip():
                    logger.error(f"No text extracted from image {file_path}")
                    return ''
                return text
            except Exception as e:
                logger.error(f"Error processing image {file_path}: {e}")
                return ''
        elif file_type in ['mp4', 'mp3']:
            logger.error(f"Audio/video processing not available in Python 3.13+")
            return ''
            # Audio processing disabled due to Python 3.13 compatibility
        else:
            logger.error(f"Unsupported file type: {file_type}")
            return ''
    except Exception as e:
        logger.error(f"General error extracting text from {file_path}: {e}")
        return ''

def extract_youtube_transcript(url, language='en'):
    try:
        video_id = url.split('v=')[1].split('&')[0]
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        text = ' '.join([entry['text'] for entry in transcript])
        if not text.strip():
            logger.error(f"No transcript extracted from YouTube URL {url}")
            return ''
        return text
    except Exception as e:
        logger.warning(f"Primary YouTube transcript extraction failed for {url}: {e}")
        try:
            ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_audio.' + info['ext'])
                ydl.download([url])
                text = extract_text_from_file(temp_path, info['ext'], language)
                os.remove(temp_path) if os.path.exists(temp_path) else None
                if not text.strip():
                    logger.error(f"No text extracted from downloaded YouTube audio {url}")
                    return ''
                return text
        except Exception as e2:
            logger.error(f"YouTube fallback extraction error for {url}: {e2}")
            return ''

def generate_gemini_summary(text, language='en'):
    try:
        if not text.strip():
            logger.error("No text provided for summary")
            return ''
        
        # Map language codes to full language names for better AI understanding
        language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
            'zh-cn': 'Chinese',
            'ja': 'Japanese',
            'ru': 'Russian',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'pt': 'Portuguese'
        }
        
        language_name = language_names.get(language.lower(), 'English')
        
        # Try Groq first (faster and you have the key!)
        groq_api_key = os.getenv('GROQ_API_KEY')
        if groq_api_key:
            try:
                client = Groq(api_key=groq_api_key)
                
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a professional summarizer. IMPORTANT: Write all summaries in {language_name} language only. Never use English or any other language unless {language_name} is English."
                        },
                        {
                            "role": "user",
                            "content": f"""Please provide a comprehensive summary of the following text.

CRITICAL INSTRUCTION: Write the ENTIRE summary in {language_name} language.

Text to summarize:
{text[:3000]}

Summary in {language_name}:""",
                        }
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.3,
                    max_tokens=800,
                    top_p=1,
                    stream=False,
                )
                
                summary = chat_completion.choices[0].message.content
                if summary.strip():
                    logger.info(f"Groq API generated summary in {language_name}")
                    return summary
            except Exception as e:
                logger.error(f"Groq API error: {e}")
        
        # Fallback to Gemini if available
        if os.getenv('GEMINI_API_KEY'):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""Please provide a comprehensive summary of the following text. 
IMPORTANT: Write the entire summary in {language_name} language only.
Do not use English or any other language. Use only {language_name}.

Text to summarize:
{text}

Summary in {language_name}:"""
            
            response = model.generate_content(prompt)
            summary = response.text
            if not summary.strip():
                logger.error("Gemini returned empty summary")
                return ' '.join(text.split()[:100]) + '...' if len(text.split()) > 100 else text
            return summary
        
        # Final fallback - just return first 100 words
        logger.warning("No API key configured for summarization")
        words = text.split()[:100]
        return ' '.join(words) + '...' if len(words) > 100 else text
        
    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        return ' '.join(text.split()[:100]) + '...' if len(text.split()) > 100 else text

def generate_gemini_answer(text, question, language='en', summary=None):
    try:
        if not text.strip() or not question.strip():
            logger.error("Text or question missing for answer")
            return f"Error: Text or question missing in {language}"
        
        # Map language codes to full language names
        language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
            'zh-cn': 'Chinese',
            'ja': 'Japanese',
            'ru': 'Russian',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'pt': 'Portuguese'
        }
        
        language_name = language_names.get(language.lower(), 'English')
        
        # Try Groq first (faster and better)
        groq_api_key = os.getenv('GROQ_API_KEY')
        if groq_api_key:
            try:
                client = Groq(api_key=groq_api_key)
                # Use summary if available (much faster), otherwise use limited text
                context = summary if summary else text[:1000]
                
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a helpful AI assistant. IMPORTANT: Answer all questions in {language_name} language only. Do not use English or any other language."
                        },
                        {
                            "role": "user",
                            "content": f"Context: {context}\n\nQuestion: {question}\n\nProvide a concise answer in {language_name}:",
                        }
                    ],
                    model="llama-3.1-8b-instant",  # Fastest model
                    temperature=0.2,  # Even lower for faster responses
                    max_tokens=300,  # Reduced further for speed
                    top_p=0.9,
                    stream=False,
                )
                
                answer = chat_completion.choices[0].message.content
                if answer.strip():
                    logger.info(f"Groq API answered in {chat_completion.usage.total_tokens} tokens")
                    return answer
            except Exception as e:
                logger.error(f"Groq API error: {e}")
        
        # Fallback to Gemini
        if os.getenv('GEMINI_API_KEY'):
            model = genai.GenerativeModel('gemini-1.5-flash')
            context = summary if summary else text[:1000]
            prompt = f"""Based on this context: {context}

Question: {question}

IMPORTANT: Provide your answer in {language_name} language only. Do not use English or any other language.

Answer in {language_name}:"""
            response = model.generate_content(prompt)
            answer = response.text
            if answer.strip():
                return answer
        
        # Final fallback
        logger.error("No API key configured")
        return f"I need an API key to answer questions. Please configure GROQ_API_KEY or GEMINI_API_KEY in the .env file."
    except Exception as e:
        logger.error(f"Answer generation error: {e}")
        return f"Error generating answer: {str(e)}"

def generate_mind_map(text):
    try:
        if not text.strip():
            logger.error("No text provided for mind map")
            return None
        
        # Use Groq first for faster concept extraction
        groq_api_key = os.getenv('GROQ_API_KEY')
        if groq_api_key:
            try:
                client = Groq(api_key=groq_api_key)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "Extract key concepts as comma-separated list. Be concise."
                        },
                        {
                            "role": "user",
                            "content": f"Extract 6-8 key concepts from this text as comma-separated list:\n\n{text[:800]}\n\nConcepts:",
                        }
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.2,
                    max_tokens=100,  # Very short for speed
                )
                concepts = [c.strip() for c in chat_completion.choices[0].message.content.split(',') if c.strip()][:8]
            except Exception as e:
                logger.error(f"Groq error in mind map: {e}")
                concepts = None
        elif os.getenv('GEMINI_API_KEY'):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Extract exactly 6-8 key concepts from this text as a comma-separated list. Only return the concepts, nothing else: {text[:1000]}"
            response = model.generate_content(prompt)
            concepts = [c.strip() for c in response.text.split(',') if c.strip()][:8]
        else:
            # Fallback: create simple mind map from text
            words = text.split()[:50]
            concepts = [' '.join(words[i:i+3]) for i in range(0, min(30, len(words)), 5)][:6]
        
        if not concepts or len(concepts) < 2:
            logger.error("Not enough concepts extracted for mind map")
            return None
        
        # Create hierarchical mind map (optimized - fewer iterations)
        G = nx.DiGraph()
        main_topic = concepts[0]
        G.add_node(main_topic)
        
        for i, concept in enumerate(concepts[1:], 1):
            G.add_node(concept)
            if i <= 3:
                G.add_edge(main_topic, concept)
            else:
                parent = concepts[((i-1) % 3) + 1]
                G.add_edge(parent, concept)
        
        plt.figure(figsize=(10, 7), facecolor='white')  # Smaller for speed
        pos = nx.spring_layout(G, k=2, iterations=30)  # Reduced iterations for speed
        
        # Draw nodes with different colors
        node_colors = ['#4e7ae7' if node == main_topic else '#7a4ee7' for node in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3000, alpha=0.9)
        nx.draw_networkx_edges(G, pos, edge_color='#cccccc', arrows=True, arrowsize=20, width=2)
        nx.draw_networkx_labels(G, pos, font_size=9, font_weight='bold', font_color='white')
        
        plt.axis('off')
        plt.tight_layout()
        
        # Save to memory buffer (reduced DPI for speed)
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')  # Reduced DPI for speed
        img_buffer.seek(0)
        plt.close()
        
        # Return base64 encoded image
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        return img_base64
    except Exception as e:
        logger.error(f"Mind map generation error: {e}")
        return None

def generate_audio_overview(text, language='en'):
    try:
        if not text.strip():
            logger.error("No text provided for audio generation")
            return jsonify({'error': 'No text provided for audio'}), 400
        
        # Map language codes for gTTS compatibility
        lang_map = {
            'en': 'en',
            'es': 'es',
            'fr': 'fr',
            'de': 'de',
            'zh': 'zh-CN',
            'zh-cn': 'zh-CN',
            'ja': 'ja',
            'ru': 'ru',
            'ar': 'ar',
            'hi': 'hi',
            'pt': 'pt'
        }
        
        gtts_lang = lang_map.get(language.lower(), 'en')
        
        # Create audio in memory buffer (no static folder)
        logger.info(f"Generating audio with language: {gtts_lang}")
        tts = gTTS(text=text, lang=gtts_lang, slow=False)
        
        # Save to memory buffer
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        # Convert to base64 for embedding
        audio_base64 = base64.b64encode(audio_buffer.getvalue()).decode('utf-8')
        
        logger.info(f"Audio generated successfully")
        return jsonify({
            'success': True, 
            'audio_base64': audio_base64,
            'filename': f'audio_overview_{int(time.time())}.mp3'
        })
    except Exception as e:
        logger.error(f"Audio generation error: {e}")
        return jsonify({'error': f'Audio generation failed: {str(e)}'}), 500

def generate_video_overview(text, language='en'):
    try:
        if not text.strip():
            logger.error("No text provided for video generation")
            return jsonify({'error': 'No text provided'}), 400
        
        # Map language codes to full language names
        language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
            'zh-cn': 'Chinese',
            'ja': 'Japanese',
            'ru': 'Russian',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'pt': 'Portuguese'
        }
        
        language_name = language_names.get(language.lower(), 'English')
        
        # Generate key points for video using Groq first
        groq_api_key = os.getenv('GROQ_API_KEY')
        if groq_api_key:
            try:
                client = Groq(api_key=groq_api_key)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a content analyzer. Extract key points in {language_name} language only."
                        },
                        {
                            "role": "user",
                            "content": f"Extract 5 key points from this text. Write each point in {language_name} language:\n\n{text[:2000]}\n\nKey points in {language_name}:",
                        }
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.3,
                    max_tokens=400,
                )
                response_text = chat_completion.choices[0].message.content
                key_points = [line.strip() for line in response_text.split('\n') if line.strip() and len(line.strip()) > 5][:5]
            except Exception as e:
                logger.error(f"Groq error in video generation: {e}")
                key_points = text.split('.')[:5]
        elif os.getenv('GEMINI_API_KEY'):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Extract 5 key points from this text as a numbered list in {language_name}: {text}"
            response = model.generate_content(prompt)
            key_points = [line.strip() for line in response.text.split('\n') if line.strip()][:5]
        else:
            sentences = text.split('.')[:5]
            key_points = [s.strip() for s in sentences if s.strip()]
        
        # Create video-like visualization (optimized for speed)
        fig, ax = plt.subplots(figsize=(10, 7), facecolor='#1a1a2e')  # Smaller for speed
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        # Title
        ax.text(5, 8.5, 'Video Overview', fontsize=22, weight='bold', 
                color='white', ha='center', va='center')
        
        # Key points
        y_position = 7
        for i, point in enumerate(key_points[:5], 1):
            point_text = point[:80] + '...' if len(point) > 80 else point
            ax.text(5, y_position, f"{i}. {point_text}", fontsize=11, 
                   color='#e0e0e0', ha='center', va='center', wrap=True)
            y_position -= 1.2
        
        plt.tight_layout()
        
        # Save to memory buffer (reduced DPI for speed)
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')  # Reduced DPI
        img_buffer.seek(0)
        plt.close()
        
        # Convert to base64 for embedding
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True, 
            'video_base64': img_base64,
            'key_points': key_points,
            'filename': f'video_overview_{int(time.time())}.png'
        })
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        return jsonify({'error': 'Video generation failed'}), 500

def generate_report_document(text, language='en'):
    try:
        if not text.strip():
            logger.error("No text provided for report")
            return jsonify({'error': 'No text provided'}), 400
        
        # Map language codes
        language_names = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'zh': 'Chinese', 'zh-cn': 'Chinese', 'ja': 'Japanese', 'ru': 'Russian',
            'ar': 'Arabic', 'hi': 'Hindi', 'pt': 'Portuguese'
        }
        language_name = language_names.get(language.lower(), 'English')
        
        # Use Groq first for faster report generation
        groq_api_key = os.getenv('GROQ_API_KEY')
        if groq_api_key:
            try:
                import json
                client = Groq(api_key=groq_api_key)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"Generate structured reports in {language_name}. Return valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": f"""Create a report in {language_name} from this text. Return ONLY valid JSON with these keys:
{{"title": "concise title", "introduction": "2 sentences", "key_points": ["point1", "point2", "point3", "point4", "point5"], "conclusion": "2 sentences"}}

Text: {text[:1500]}

JSON:""",
                        }
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.2,
                    max_tokens=500,
                )
                report_data = json.loads(chat_completion.choices[0].message.content.strip())
            except Exception as e:
                logger.error(f"Groq error in report: {e}")
                report_data = {
                    'title': 'Summary Report',
                    'introduction': text[:200] + '...',
                    'key_points': text.split('.')[:5],
                    'conclusion': 'This report summarizes the key information.'
                }
        elif os.getenv('GEMINI_API_KEY'):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""Create a structured report from this text in {language_name}. Format as JSON with these keys:
            - title: A concise title
            - introduction: 2-3 sentence introduction
            - key_points: Array of 5-7 main points
            - conclusion: 2-3 sentence conclusion
            
            Text: {text}"""
            
            response = model.generate_content(prompt)
            try:
                import json
                report_data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
            except:
                report_data = {
                    'title': 'Summary Report',
                    'introduction': text[:200] + '...',
                    'key_points': text.split('.')[:5],
                    'conclusion': text[-200:] if len(text) > 200 else text
                }
        else:
            report_data = {
                'title': 'Summary Report',
                'introduction': text[:200] + '...',
                'key_points': text.split('.')[:5],
                'conclusion': 'This report summarizes the key information from the provided content.'
            }
        
        # Create HTML report
        html_report = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2c3e50; border-bottom: 3px solid #4e7ae7; padding-bottom: 10px;">
                {report_data.get('title', 'Summary Report')}
            </h1>
            
            <h2 style="color: #4e7ae7; margin-top: 30px;">Introduction</h2>
            <p style="line-height: 1.8; color: #333;">
                {report_data.get('introduction', '')}
            </p>
            
            <h2 style="color: #4e7ae7; margin-top: 30px;">Key Points</h2>
            <ul style="line-height: 2; color: #333;">
                {''.join([f'<li>{point}</li>' for point in report_data.get('key_points', [])])}
            </ul>
            
            <h2 style="color: #4e7ae7; margin-top: 30px;">Conclusion</h2>
            <p style="line-height: 1.8; color: #333;">
                {report_data.get('conclusion', '')}
            </p>
            
            <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px;">
                Generated by Smart Summarizer
            </div>
        </div>
        """
        
        return jsonify({
            'success': True,
            'report_html': html_report,
            'report_data': report_data
        })
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        return jsonify({'error': 'Report generation failed'}), 500

def download_report_pdf(text, report_data):
    try:
        timestamp = int(time.time())
        filename = f'report_{timestamp}.pdf'
        filepath = os.path.join('static', filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#2c3e50',
            spaceAfter=30
        )
        story.append(Paragraph(report_data.get('title', 'Summary Report'), title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Introduction
        story.append(Paragraph('<b>Introduction</b>', styles['Heading2']))
        story.append(Paragraph(report_data.get('introduction', ''), styles['BodyText']))
        story.append(Spacer(1, 0.2*inch))
        
        # Key Points
        story.append(Paragraph('<b>Key Points</b>', styles['Heading2']))
        for point in report_data.get('key_points', []):
            story.append(Paragraph(f'• {point}', styles['BodyText']))
        story.append(Spacer(1, 0.2*inch))
        
        # Conclusion
        story.append(Paragraph('<b>Conclusion</b>', styles['Heading2']))
        story.append(Paragraph(report_data.get('conclusion', ''), styles['BodyText']))
        
        doc.build(story)
        
        return f'/static/{filename}'
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return None

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index.html: {e}")
        return jsonify({'error': 'Template not found or server error'}), 500

@app.route('/next')
def next_page():
    try:
        return render_template('next.html')
    except Exception as e:
        logger.error(f"Error rendering next.html: {e}")
        return jsonify({'error': 'Template not found or server error'}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            logger.error("No file part in upload request")
            return jsonify({'error': 'No file part in request'}), 400
        file = request.files['file']
        language = request.form.get('language', 'en')
        if language not in SUPPORTED_LANGUAGES:
            logger.error(f"Unsupported language: {language}")
            return jsonify({'error': f"Unsupported language: {language}"}), 400
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No file selected'}), 400
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(file_path)
        except Exception as e:
            logger.error(f"Error saving file {filename}: {e}")
            return jsonify({'error': 'Failed to save file'}), 500
        file_type = filename.split('.')[-1].lower()
        text = extract_text_from_file(file_path, file_type, language)
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Error removing file {file_path}: {e}")
        if not text:
            logger.error(f"No text extracted from {filename}")
            return jsonify({'error': f"Failed to extract text from {filename}. File may be empty, corrupted, or not supported."}), 400
        summary = generate_gemini_summary(text, language)
        if not summary:
            logger.error(f"No summary generated for {filename}")
            return jsonify({'error': 'Failed to generate summary'}), 400
        return jsonify({'success': True, 'text': text, 'summary': summary})
    except Exception as e:
        logger.error(f"Upload endpoint error: {e}")
        return jsonify({'error': f"Server error during file upload: {str(e)}"}), 500

@app.route('/summarize_url', methods=['POST'])
def summarize_url():
    try:
        data = request.get_json()
        url = data.get('url', '')
        language = data.get('language', 'en')
        if language not in SUPPORTED_LANGUAGES:
            logger.error(f"Unsupported language: {language}")
            return jsonify({'error': f"Unsupported language: {language}"}), 400
        if not url:
            logger.error("No URL provided")
            return jsonify({'error': 'No URL provided'}), 400
        if 'youtube.com' in url or 'youtu.be' in url:
            text = extract_youtube_transcript(url, language)
        else:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                text = ' '.join([p.get_text() for p in soup.find_all('p') if p.get_text().strip()])
            except Exception as e:
                logger.error(f"Error fetching URL {url}: {e}")
                text = ''
        if not text:
            logger.error(f"No text extracted from URL {url}")
            return jsonify({'error': 'No text extracted from URL'}), 400
        summary = generate_gemini_summary(text, language)
        if not summary:
            logger.error(f"No summary generated for URL {url}")
            return jsonify({'error': 'Failed to generate summary for URL'}), 400
        return jsonify({'success': True, 'text': text, 'summary': summary})
    except Exception as e:
        logger.error(f"URL summarization error: {e}")
        return jsonify({'error': f"Server error during URL processing: {str(e)}"}), 500

@app.route('/generate_summary', methods=['POST'])
def generate_summary():
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')
        if not text:
            logger.error("No text provided for summary")
            return jsonify({'error': 'No text provided'}), 400
        summary = generate_gemini_summary(text, language)
        if not summary:
            logger.error("No summary generated")
            return jsonify({'error': 'Failed to generate summary'}), 400
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        return jsonify({'error': f"Server error during summary generation: {str(e)}"}), 500

@app.route('/ask_question', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        text = data.get('text', '')
        summary = data.get('summary', '')  # Get summary for faster responses
        question = data.get('question', '')
        language = data.get('language', 'en')
        if not text or not question:
            logger.error("Text or question missing")
            return jsonify({'error': 'Text or question missing'}), 400
        answer = generate_gemini_answer(text, question, language, summary)
        if not answer:
            logger.error("No answer generated")
            return jsonify({'error': 'Failed to generate answer'}), 400
        return jsonify({'success': True, 'answer': answer})
    except Exception as e:
        logger.error(f"Question answering error: {e}")
        return jsonify({'error': f"Server error during question answering: {str(e)}"}), 500

@app.route('/generate_mindmap', methods=['POST'])
def generate_mindmap():
    try:
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            logger.error("No text provided for mind map")
            return jsonify({'error': 'No text provided'}), 400
        img_base64 = generate_mind_map(text)
        if img_base64:
            return jsonify({
                'success': True, 
                'mindmap_base64': img_base64,
                'filename': f'mindmap_{int(time.time())}.png'
            })
        else:
            return jsonify({'error': 'Failed to generate mind map'}), 400
    except Exception as e:
        logger.error(f"Mind map endpoint error: {e}")
        return jsonify({'error': f"Server error during mind map generation: {str(e)}"}), 500

@app.route('/studio/audio', methods=['POST'])
def studio_audio():
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        return generate_audio_overview(text, language)
    except Exception as e:
        logger.error(f"Studio audio error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/studio/video', methods=['POST'])
def studio_video():
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        return generate_video_overview(text, language)
    except Exception as e:
        logger.error(f"Studio video error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/studio/mindmap', methods=['POST'])
def studio_mindmap():
    try:
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        img_base64 = generate_mind_map(text)
        if img_base64:
            return jsonify({
                'success': True, 
                'mindmap_base64': img_base64,
                'filename': f'mindmap_{int(time.time())}.png'
            })
        else:
            return jsonify({'error': 'Failed to generate mind map'}), 400
    except Exception as e:
        logger.error(f"Studio mindmap error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/studio/report', methods=['POST'])
def studio_report():
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        return generate_report_document(text, language)
    except Exception as e:
        logger.error(f"Studio report error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_report_pdf', methods=['POST'])
def download_report_pdf_endpoint():
    try:
        data = request.get_json()
        text = data.get('text', '')
        report_data = data.get('report_data', {})
        
        pdf_path = download_report_pdf(text, report_data)
        if pdf_path:
            return jsonify({'success': True, 'pdf_url': pdf_path})
        else:
            return jsonify({'error': 'Failed to generate PDF'}), 400
    except Exception as e:
        logger.error(f"PDF download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_summary', methods=['POST'])
def download_summary_endpoint():
    try:
        data = request.get_json()
        summary = data.get('summary', '')
        format_type = data.get('format', 'txt')
        
        if not summary:
            return jsonify({'error': 'No summary provided'}), 400
        
        timestamp = int(time.time())
        
        if format_type == 'txt':
            filename = f'summary_{timestamp}.txt'
            filepath = os.path.join('static', filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(summary)
            return jsonify({'success': True, 'download_url': f'/static/{filename}'})
        
        elif format_type == 'pdf':
            filename = f'summary_{timestamp}.pdf'
            filepath = os.path.join('static', filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=30
            )
            story.append(Paragraph('Summary', title_style))
            story.append(Paragraph(summary, styles['BodyText']))
            
            doc.build(story)
            return jsonify({'success': True, 'download_url': f'/static/{filename}'})
        
        elif format_type == 'docx':
            filename = f'summary_{timestamp}.docx'
            filepath = os.path.join('static', filename)
            
            doc = docx.Document()
            doc.add_heading('Summary', 0)
            doc.add_paragraph(summary)
            doc.save(filepath)
            
            return jsonify({'success': True, 'download_url': f'/static/{filename}'})
        
        else:
            return jsonify({'error': 'Invalid format'}), 400
            
    except Exception as e:
        logger.error(f"Download summary error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/ping')
def ping():
    groq_key = os.getenv('GROQ_API_KEY')
    return jsonify({
        'success': True, 
        'message': 'Server is running',
        'groq_configured': bool(groq_key),
        'groq_key_prefix': groq_key[:10] if groq_key else None
    })

@app.route('/cleanup')
def cleanup():
    cleanup_old_files()
    return jsonify({'success': True, 'message': 'Cleanup completed'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)