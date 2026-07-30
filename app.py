from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import re
from datetime import datetime
import random
import os

app = Flask(__name__)
CORS(app)

# ===== LANGUAGE DICTIONARY (Keep your existing one) =====
# ... (your LANGUAGES dictionary here, it's the same) ...

# ===== DEEPSEEK API =====
def generate_article(topic, year=None):
    """Generate a complete article using DeepSeek AI"""
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    
    if not deepseek_key:
        return None
    
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {deepseek_key}",
            "Content-Type": "application/json"
        }
        
        year_text = f" in {year}" if year else ""
        
        prompt = f"""Write a complete, self-contained article about {topic}{year_text}.

The article should:
- Be 150-200 words long
- Include key historical facts and context
- Be written in a clear, engaging style
- Stand alone as a complete article (no external links needed)
- End with a memorable conclusion

Write the article in English:"""
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a professional historian writing engaging, self-contained articles for a history app."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 400
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            article = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if article and len(article) > 50:
                return article.strip()
        
        return None
    except Exception as e:
        print(f"DeepSeek error: {e}")
        return None

def get_fallback_article(topic, year):
    """Return a fallback article if AI fails"""
    fallbacks = {
        '1914': f"📜 **{topic}**\n\nThis event occurred in {year}, a year that shaped the course of history. The events of {year} had far-reaching consequences that would influence generations to come. Historians continue to study this period to understand its impact on modern society.\n\n💡 The story of {year} reminds us how history connects us all.",
        '1945': f"📜 **{topic}**\n\n{year} was a pivotal year in world history. The events that unfolded during this time changed the global landscape forever. From political shifts to technological breakthroughs, {year} stands as a testament to humanity's resilience.\n\n💡 Every year has its story, and {year} is no exception.",
        '1976': f"📜 **{topic}**\n\nIn {year}, the world witnessed events that would be remembered for decades. This year was marked by significant developments that shaped the modern era. The legacy of {year} continues to influence our world today.\n\n💡 History is made every day, and {year} was no different."
    }
    
    if year and year in fallbacks:
        return fallbacks[year]
    
    return f"📜 **{topic}**\n\nThis significant event in {year} represents an important moment in history. While the full details of this event can be explored further, its impact on the world stage was undeniable. Understanding our past helps us build a better future.\n\n💡 Every historical event has a story worth telling."

# ===== ROUTES =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/languages')
def get_languages():
    return jsonify(LANGUAGES)

@app.route('/api/events')
def get_events():
    month = request.args.get('month', type=int)
    day = request.args.get('day', type=int)
    
    if not month or not day:
        now = datetime.now()
        month = now.month
        day = now.day
    
    events_list, births_list, deaths_list = [], [], []
    
    try:
        url = f"https://api.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            for e in r.json().get('events', [])[:10]:
                events_list.append({
                    'year': str(e.get('year', '?')),
                    'text': re.sub(r'<[^>]+>', '', e.get('text', ''))[:150]
                })
    except:
        pass
    
    try:
        url = f"https://api.wikipedia.org/api/rest_v1/feed/onthisday/births/{month}/{day}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            for e in r.json().get('births', [])[:6]:
                births_list.append({
                    'year': str(e.get('year', '?')),
                    'text': re.sub(r'<[^>]+>', '', e.get('text', ''))[:120]
                })
    except:
        pass
    
    try:
        url = f"https://api.wikipedia.org/api/rest_v1/feed/onthisday/deaths/{month}/{day}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            for e in r.json().get('deaths', [])[:6]:
                deaths_list.append({
                    'year': str(e.get('year', '?')),
                    'text': re.sub(r'<[^>]+>', '', e.get('text', ''))[:120]
                })
    except:
        pass
    
    if not events_list and not births_list and not deaths_list:
        events_list = [
            {'year': '1914', 'text': 'World War I began when Austria-Hungary declared war on Serbia'},
            {'year': '1945', 'text': 'A US Army bomber crashed into the Empire State Building'},
            {'year': '1976', 'text': 'The Tangshan earthquake in China killed over 240,000 people'},
            {'year': '1996', 'text': 'The remains of a woolly mammoth were discovered in Siberia'}
        ]
        births_list = [
            {'year': '1804', 'text': 'Ludwig Feuerbach, German philosopher'},
            {'year': '1929', 'text': 'Jacqueline Kennedy Onassis, First Lady of the United States'},
            {'year': '1938', 'text': 'Alberto Fujimori, President of Peru'},
            {'year': '1954', 'text': 'Hugo Chávez, President of Venezuela'}
        ]
        deaths_list = [
            {'year': '1750', 'text': 'Johann Sebastian Bach, German composer'},
            {'year': '2004', 'text': 'Francis Crick, co-discoverer of DNA structure'},
            {'year': '2015', 'text': 'Edward Natapei, Prime Minister of Vanuatu'}
        ]
    
    return jsonify({
        'events': events_list,
        'births': births_list,
        'deaths': deaths_list
    })

@app.route('/api/article')
def get_article():
    """Get a complete, self-contained article for an event"""
    query = request.args.get('title', '')
    if not query:
        return jsonify({'error': 'No title provided'}), 400
    
    # Extract year
    year_match = re.search(r'\b(\d{4})\b', query)
    year = year_match.group(1) if year_match else None
    
    # Clean the query
    clean_query = re.sub(r'[^\w\s]', '', query)
    clean_query = ' '.join(clean_query.split())
    
    # Try to generate article with AI
    article = generate_article(clean_query, year)
    
    if article:
        return jsonify({
            'title': f"📜 {clean_query}",
            'content': article,
            'source': 'ai_generated'
        })
    
    # Fallback article if AI fails
    fallback = get_fallback_article(clean_query, year)
    return jsonify({
        'title': f"📜 {clean_query}",
        'content': fallback,
        'source': 'fallback'
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'History API is running!'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
