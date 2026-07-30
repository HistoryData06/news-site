from flask import Flask, render_template, jsonify
from flask_cors import CORS
import requests
import feedparser
import re
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# ===== NEWS SOURCES =====
NEWS_SOURCES = [
    {'name': 'BBC World', 'url': 'http://feeds.bbci.co.uk/news/world/rss.xml', 'category': 'World'},
    {'name': 'BBC Tech', 'url': 'http://feeds.bbci.co.uk/news/technology/rss.xml', 'category': 'Tech'},
    {'name': 'BBC Business', 'url': 'http://feeds.bbci.co.uk/news/business/rss.xml', 'category': 'Business'},
    {'name': 'CNN Top Stories', 'url': 'http://rss.cnn.com/rss/cnn_topstories.rss', 'category': 'World'},
    {'name': 'Reuters World', 'url': 'https://www.reuters.com/feeds/reuters-news.rss', 'category': 'World'},
    {'name': 'Al Jazeera', 'url': 'https://www.aljazeera.com/xml/rss/all.xml', 'category': 'World'},
    {'name': 'Science Daily', 'url': 'https://www.sciencedaily.com/rss/all.xml', 'category': 'Science'},
    {'name': 'The Guardian', 'url': 'https://www.theguardian.com/world/rss', 'category': 'World'},
    {'name': 'TechCrunch', 'url': 'https://techcrunch.com/feed/', 'category': 'Tech'},
    {'name': 'ESPN', 'url': 'https://www.espn.com/espn/rss/news', 'category': 'Sports'},
    {'name': 'BBC Health', 'url': 'https://www.bbc.co.uk/news/health/rss.xml', 'category': 'Health'},
    {'name': 'BBC Entertainment', 'url': 'https://www.bbc.co.uk/news/entertainment_and_arts/rss.xml', 'category': 'Entertainment'},
]

def clean_html(text):
    """Remove HTML tags from text"""
    return re.sub(r'<[^>]+>', '', text)

def rewrite_article(title, summary):
    """Rewrite the article in a unique, engaging way using AI"""
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    
    if not deepseek_key:
        return summary
    
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {deepseek_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Rewrite this news article in a unique, engaging way for a news app:

Original Title: {title}
Original Content: {summary}

Requirements:
- Make it sound fresh and interesting
- Keep it to 2-3 sentences (max 60 words)
- Don't just copy the original - rewrite it in your own words
- Make it engaging for readers

Rewritten version:"""
        
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 100
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            rewritten = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if rewritten and len(rewritten) > 10:
                return rewritten.strip()
        
        return summary
    except Exception as e:
        print(f"AI rewrite error: {e}")
        return summary

def get_articles():
    """Fetch articles from all news sources"""
    all_articles = []
    
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source['url'])
            
            for entry in feed.entries[:5]:
                # Clean up the summary
                summary = clean_html(entry.get('summary', ''))
                summary = summary[:250] + '...' if len(summary) > 250 else summary
                
                # Get image if available
                image = ''
                if 'media_thumbnail' in entry:
                    image = entry.media_thumbnail[0]['url']
                elif 'media_content' in entry and entry.media_content:
                    image = entry.media_content[0].get('url', '')
                
                # Get published date
                published = entry.get('published', '')
                if not published and 'published_parsed' in entry:
                    if entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6]).isoformat()
                
                all_articles.append({
                    'title': entry.get('title', 'No title'),
                    'summary': summary,
                    'link': entry.get('link', ''),
                    'source': source['name'],
                    'category': source['category'],
                    'published': published,
                    'image': image,
                    'rewritten': False
                })
        except Exception as e:
            print(f"Error fetching {source['name']}: {e}")
    
    # Sort by date (newest first)
    all_articles.sort(key=lambda x: x['published'], reverse=True)
    return all_articles

# ===== ROUTES =====
@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/news')
def api_news():
    """API endpoint for news with AI-rewritten articles"""
    articles = get_articles()
    
    # Rewrite the first 5 articles
    for i, article in enumerate(articles[:5]):
        if article.get('summary') and len(article['summary']) > 30:
            rewritten = rewrite_article(article['title'], article['summary'])
            if rewritten:
                articles[i]['summary'] = rewritten
                articles[i]['rewritten'] = True
    
    return jsonify({
        'articles': articles,
        'total': len(articles),
        'sources': len(NEWS_SOURCES),
        'ai_rewrite_enabled': True
    })

@app.route('/api/categories')
def api_categories():
    """Get all categories"""
    categories = list(set(s['category'] for s in NEWS_SOURCES))
    return jsonify({'categories': sorted(categories)})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'News API is running!'})

# ===== START SERVER =====
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
