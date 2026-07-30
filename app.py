from flask import Flask, render_template, jsonify
from flask_cors import CORS
import requests
import feedparser
import re
from datetime import datetime
import os

app = Flask(__name__)
CORS(app, origins=["https://news-site-klur.onrender.com", "http://localhost:5000", "*"])

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
    """Fetch articles from all news sources with better image extraction"""
    all_articles = []
    
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source['url'])
            
            for entry in feed.entries[:5]:
                # Clean up the summary
                summary = clean_html(entry.get('summary', ''))
                summary = summary[:250] + '...' if len(summary) > 250 else summary
                
                # ===== BETTER IMAGE EXTRACTION =====
                image = ''
                
                # Try 1: media_thumbnail (most common)
                if 'media_thumbnail' in entry and entry.media_thumbnail:
                    image = entry.media_thumbnail[0]['url']
                
                # Try 2: media_content
                elif 'media_content' in entry and entry.media_content:
                    for content in entry.media_content:
                        if 'url' in content:
                            image = content['url']
                            break
                
                # Try 3: links with image types
                elif 'links' in entry:
                    for link in entry.links:
                        if link.get('type', '').startswith('image/'):
                            image = link.get('href', '')
                            break
                
                # Try 4: Extract from summary HTML
                if not image and 'summary' in entry:
                    img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
                    if img_match:
                        image = img_match.group(1)
                
                # Try 5: Extract from content
                if not image and 'content' in entry:
                    for content_item in entry.content:
                        img_match = re.search(r'<img[^>]+src="([^">]+)"', content_item.value)
                        if img_match:
                            image = img_match.group(1)
                            break
                
                # Try 6: Use a default image if still no image
                if not image:
                    # Use a category-specific default image
                    category_images = {
                        'World': 'https://via.placeholder.com/400x200/1a1a1a/ff4a4a?text=🌍+World+News',
                        'Tech': 'https://via.placeholder.com/400x200/1a1a1a/ff4a4a?text=💻+Tech+News',
                        'Business': 'https://via.placeholder.com/400x200/1a1a1a/ff4a4a?text=📈+Business',
                        'Science': 'https://via.placeholder.com/400x200/1a1a1a/ff4a4a?text=🔬+Science',
                        'Sports': 'https://via.placeholder.com/400x200/1a1a1a/ff4a4a?text=⚽+Sports',
                        'Health': 'https://via.placeholder.com/400x200/1a1a1a/ff4a4a?text=🏥+Health',
                        'Entertainment': 'https://via.placeholder.com/400x200/1a1a1a/ff4a4a?text=🎬+Entertainment',
                    }
                    image = category_images.get(source['category'], 'https://via.placeholder.com/400x200/1a1a1a/ff4a4a?text=📰+News')
                
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
    return render_template('index.html')

@app.route('/api/news')
def api_news():
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
    categories = list(set(s['category'] for s in NEWS_SOURCES))
    return jsonify({'categories': sorted(categories)})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'News API is running!'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
