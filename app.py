from flask import Flask, render_template, jsonify
from flask_cors import CORS
import requests
import feedparser
import re
from datetime import datetime
import os
from bs4 import BeautifulSoup

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
    return re.sub(r'<[^>]+>', '', text)

def fetch_article_image(article_url):
    if not article_url:
        return None
    try:
        response = requests.get(article_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return og_image['content']
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                return twitter_image['content']
    except:
        pass
    return None

def extract_image_from_entry(entry, category='General'):
    image = None
    if 'media_thumbnail' in entry and entry.media_thumbnail:
        image = entry.media_thumbnail[0]['url']
    if not image and 'media_content' in entry and entry.media_content:
        for content in entry.media_content:
            if 'url' in content:
                image = content['url']
                break
    if not image and entry.get('link'):
        image = fetch_article_image(entry.get('link'))
    if not image:
        category_images = {
            'World': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=World+News',
            'Tech': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Tech+News',
            'Business': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Business',
            'Science': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Science',
            'Sports': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Sports',
            'Health': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Health',
            'Entertainment': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Entertainment',
        }
        image = category_images.get(category, 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=News')
    return image

def calculate_read_time(text):
    words = len(text.split())
    return max(1, round(words / 200))

def get_articles():
    all_articles = []
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source['url'])
            for entry in feed.entries[:5]:
                summary = clean_html(entry.get('summary', ''))[:250] + '...'
                title = entry.get('title', 'No title')
                image = extract_image_from_entry(entry, source['category'])
                read_time = calculate_read_time(title + ' ' + summary)
                published = entry.get('published', '')
                if not published and 'published_parsed' in entry:
                    if entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6]).isoformat()
                all_articles.append({
                    'title': title,
                    'summary': summary,
                    'link': entry.get('link', ''),
                    'source': source['name'],
                    'category': source['category'],
                    'published': published,
                    'image': image,
                    'read_time': read_time,
                    'rewritten': False
                })
        except Exception as e:
            print(f"Error fetching {source['name']}: {e}")
    all_articles.sort(key=lambda x: x['published'], reverse=True)
    return all_articles

# ===== ROUTES =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news')
def api_news():
    articles = get_articles()
    return jsonify({
        'articles': articles,
        'total': len(articles),
        'sources': len(NEWS_SOURCES)
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
