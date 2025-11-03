#!/usr/bin/env python3
"""
Flask API Server for RSS Feed Aggregator
Integrates gather and translate modules with real-time frontend updates
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
import json
import os
import sys

# Add the pipeline directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'pipeline'))

from gather import gather
from translate import Translator

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
current_headlines = []
processing_status = "idle"
current_task = ""
progress = 0
total_items = 0

def emit_status_update(status, task, progress=0, total=0, message=""):
    data = {
        "status": status,
        "task": task,
        "progress": int(progress),
        "total": int(total),
        "message": message,
        "timestamp": time.time()
    }
    socketio.emit('status_update', data)
    print(f"Status: {status} | Task: {task} | Progress: {progress}/{total} | {message}")

def emit_headline_update(headlines, message=""):
    data = {
        "headlines": headlines,
        "message": message,
        "timestamp": time.time()
    }
    socketio.emit('headlines_update', data)

def emit_log_message(level, message):
    data = {
        "level": level,
        "message": message,
        "timestamp": time.time()
    }
    socketio.emit('log_message', data)

def gather_headlines_with_progress():
    global current_headlines, processing_status, current_task, progress, total_items
    try:
        processing_status = "gathering"
        current_task = "Gathering RSS feeds"
        progress = 0
        emit_status_update("gathering", current_task, progress, 0, "Starting RSS feed collection...")
        emit_log_message("info", "🚀 Starting RSS feed collection process...")

        from gather import feedList
        total_feeds = len(feedList)
        total_items = total_feeds
        emit_status_update("gathering", current_task, progress, total_feeds, f"Found {total_feeds} RSS feeds to process")

        # Capture prints from gather()
        original_print = print
        def progress_print(*args, **kwargs):
            message = " ".join(str(arg) for arg in args)
            original_print(message)
            if "Processing" in message and "/" in message:
                try:
                    parts = message.split("Processing ")[1].split(":")[0]
                    cur, tot = parts.split("/")
                    emit_status_update("gathering", current_task, int(cur), int(tot), f"Processing feed {cur}/{tot}")
                except Exception:
                    pass
            elif message.startswith("Added "):
                emit_log_message("success", f"✅ {message}")
            elif message.startswith("Warning:") or message.startswith("Skipping"):
                emit_log_message("warning", f"⚠️ {message}")
            elif message.startswith("Error"):
                emit_log_message("error", f"❌ {message}")

        import builtins
        builtins.print = progress_print
        headlines = gather()
        builtins.print = original_print

        current_headlines = headlines or []
        processing_status = "gathered"
        progress = total_feeds
        emit_status_update("gathered", "RSS feeds gathered", progress, total_feeds, f"Successfully collected {len(current_headlines)} headlines")
        emit_log_message("success", f"🎉 Collected {len(current_headlines)} headlines")
        emit_headline_update(current_headlines, f"Collected {len(current_headlines)} headlines")
        return current_headlines
    except Exception as e:
        processing_status = "error"
        msg = f"Error during gathering: {str(e)}"
        emit_status_update("error", "Gathering failed", 0, 0, msg)
        emit_log_message("error", f"💥 {msg}")
        raise

def translate_headlines_with_progress():
    global current_headlines, processing_status, current_task, progress, total_items
    try:
        if not current_headlines:
            emit_log_message("warning", "⚠️ No headlines to translate. Please gather headlines first.")
            return []

        # Determine items requiring translation
        translatable_indices = [idx for idx, h in enumerate(current_headlines)
                                if h.get('language') != 'en' and not h.get('translated')]
        total_items = len(translatable_indices)
        if total_items == 0:
            emit_log_message("info", "ℹ️ All headlines are already in English or previously translated")
            return current_headlines

        processing_status = "translating"
        current_task = "Translating headlines"
        progress = 0
        emit_status_update("translating", current_task, progress, total_items, f"Starting translation of {total_items} headlines...")
        emit_log_message("info", f"🌍 Starting translation process for {total_items} headlines...")

        translator = Translator()

        # OPTIMIZED: Prepare batch data in single pass
        texts_to_translate = []
        langs_to_translate = []
        for idx in translatable_indices:
            headline = current_headlines[idx]
            texts_to_translate.append(headline.get('title', ''))
            langs_to_translate.append(headline.get('language', 'unknown'))
        
        emit_log_message("info", f"📦 Prepared batch of {len(texts_to_translate)} texts for translation")
        
        # OPTIMIZED: Single batch translation call
        try:
            translated_texts = translator.translate_batch(texts_to_translate, langs_to_translate)
            emit_log_message("success", f"✅ Batch translation completed")
        except Exception as e:
            emit_log_message("error", f"❌ Batch translation failed: {str(e)}, falling back to individual translation")
            # Fallback to individual translation
            translated_texts = []
            for text, lang in zip(texts_to_translate, langs_to_translate):
                try:
                    translated = translator.translate_text(text, lang)
                    translated_texts.append(translated if translated else text)
                except Exception as ind_error:
                    emit_log_message("error", f"❌ Individual translation error: {str(ind_error)}")
                    translated_texts.append(text)
        
        # OPTIMIZED: Update headlines in single loop
        processed = 0
        for idx, translated_title in zip(translatable_indices, translated_texts):
            headline = current_headlines[idx]
            original_title = headline.get('title', '')
            src_lang = headline.get('language', 'unknown')
            
            try:
                # Mark as translated if we got a result
                if translated_title:
                    # Preserve original title BEFORE overwriting
                    if 'original_title' not in headline:
                        headline['original_title'] = original_title
                    
                    # Only update title if translation is different (real translation)
                    if translated_title != original_title:
                        headline['title'] = translated_title
                        headline['translated'] = True
                        emit_log_message("success", f"✅ Translated [{src_lang}] {headline.get('source','')} ")
                    else:
                        # Mock mode or already English - still mark as processed
                        headline['translated'] = True
                        emit_log_message("info", f"ℹ️ Processed [{src_lang}] {headline.get('source','')} (mock/English)")
                else:
                    # Translation failed
                    headline['translated'] = False
                    emit_log_message("warning", f"⚠️ Translation failed for: {headline.get('source','')}")
            except Exception as e:
                emit_log_message("error", f"❌ Translation error for index {idx}: {str(e)}")
                headline['translated'] = False
            finally:
                processed += 1
                progress = processed
                # Update progress less frequently for better performance
                if processed % 10 == 0 or processed == total_items:
                    emit_status_update("translating", current_task, progress, total_items, f"Translated {progress}/{total_items} headlines")

        processing_status = "translated"
        translated_count = sum(1 for h in current_headlines if h.get('translated'))
        emit_status_update("translated", "Translation completed", total_items, total_items, f"Translation completed! {translated_count} headlines translated")
        emit_log_message("success", f"🎉 Translation completed! {translated_count} headlines translated")
        emit_headline_update(current_headlines, f"Translation completed - {translated_count} headlines translated")
        return current_headlines
    except Exception as e:
        processing_status = "error"
        msg = f"Error during translation: {str(e)}"
        emit_status_update("error", "Translation failed", 0, 0, msg)
        emit_log_message("error", f"💥 {msg}")
        raise

# API Endpoints
@app.route('/api/headlines', methods=['GET'])
def get_headlines():
    return jsonify({
        "headlines": current_headlines,
        "status": processing_status,
        "count": len(current_headlines)
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "status": processing_status,
        "task": current_task,
        "progress": progress,
        "total": total_items,
        "headlines_count": len(current_headlines)
    })

@app.route('/api/gather', methods=['POST'])
def start_gathering():
    auto_translate = request.args.get('translate', default='1') in ('1', 'true', 'yes')

    def gather_worker():
        try:
            gather_headlines_with_progress()
            if auto_translate:
                emit_log_message("info", "▶️ Auto-translate enabled: starting translation after gather...")
                translate_headlines_with_progress()
        except Exception as e:
            emit_log_message("error", f"💥 Gathering process failed: {str(e)}")

    thread = threading.Thread(target=gather_worker)
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Gathering process started", "status": "started", "auto_translate": auto_translate})

@app.route('/api/translate', methods=['POST'])
def start_translation():
    def translate_worker():
        try:
            translate_headlines_with_progress()
        except Exception as e:
            emit_log_message("error", f"💥 Translation process failed: {str(e)}")

    thread = threading.Thread(target=translate_worker)
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Translation process started", "status": "started"})

@app.route('/api/feeds', methods=['GET'])
def get_feeds():
    try:
        from gather import feedList
        return jsonify({
            "feeds": feedList,
            "count": len(feedList)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected to RSS Feed Aggregator'})
    emit_log_message("info", "🔌 Frontend connected")
    emit('status_update', {
        "status": processing_status,
        "task": current_task,
        "progress": progress,
        "total": total_items,
        "timestamp": time.time()
    })

@socketio.on('disconnect')
def handle_disconnect():
    emit_log_message("info", "🔌 Frontend disconnected")

if __name__ == '__main__':
    print("🚀 Starting RSS Feed Aggregator API Server...")
    print("📱 Frontend will be available at: http://localhost:3000")
    print("🔌 API Server will be available at: http://localhost:5050")
    print("📡 WebSocket will be available at: ws://localhost:5050")
    socketio.run(app, host='0.0.0.0', port=5050, debug=True, allow_unsafe_werkzeug=True) 