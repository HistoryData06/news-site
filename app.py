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
    """Remove HTML tags from text"""
    return re.sub(r'<[^>]+>', '', text)

def calculate_read_time(text):
    """Calculate reading time in minutes"""
    # Average reading speed: 200 words per minute
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return minutes

def fetch_article_image(article_url):
    """Visit the article page and extract the main image URL"""
    if not article_url:
        return None
    
    try:
        response = requests.get(article_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                img_url = og_image['content']
                if not img_url.startswith('http'):
                    img_url = requests.compat.urljoin(article_url, img_url)
                return img_url
            
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                img_url = twitter_image['content']
                if not img_url.startswith('http'):
                    img_url = requests.compat.urljoin(article_url, img_url)
                return img_url
            
            main_content = soup.find('article') or soup.find('main') or soup.find('div', class_='content') or soup.find('body')
            if main_content:
                img = main_content.find('img')
                if img and img.get('src'):
                    img_src = img['src']
                    if not img_src.startswith('http'):
                        img_src = requests.compat.urljoin(article_url, img_src)
                    return img_src
            
            all_images = soup.find_all('img')
            for img in all_images:
                if img.get('src'):
                    src = img['src']
                    if 'logo' in src.lower() or 'icon' in src.lower() or 'avatar' in src.lower():
                        continue
                    if not src.startswith('http'):
                        src = requests.compat.urljoin(article_url, src)
                    return src
                    
    except Exception as e:
        print(f"Error fetching image from {article_url}: {e}")
    
    return None

def extract_image_from_entry(entry, category='General', title=''):
    """Extract image from RSS entry or fetch from article page"""
    image = None
    
    if 'media_thumbnail' in entry and entry.media_thumbnail:
        image = entry.media_thumbnail[0]['url']
    
    if not image and 'media_content' in entry and entry.media_content:
        for content in entry.media_content:
            if 'url' in content:
                image = content['url']
                break
    
    if not image and 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                image = link.get('href', '')
                break
    
    if not image and 'summary' in entry:
        img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
        if img_match:
            image = img_match.group(1)
    
    if not image and 'content' in entry:
        for content_item in entry.content:
            img_match = re.search(r'<img[^>]+src="([^">]+)"', content_item.value)
            if img_match:
                image = img_match.group(1)
                break
    
    if not image and entry.get('link'):
        article_url = entry.get('link')
        image = fetch_article_image(article_url)
    
    if not image:
        category_placeholders = {
            'World': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=World+News',
            'Tech': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Tech+News',
            'Business': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Business',
            'Science': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Science',
            'Sports': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Sports',
            'Health': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Health',
            'Entertainment': 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=Entertainment',
        }
        image = category_placeholders.get(category, 'https://placehold.co/600x400/1a1a1a/ff4a4a?text=News')
    
    return image

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
                summary = clean_html(entry.get('summary', ''))
                summary = summary[:250] + '...' if len(summary) > 250 else summary
                
                title = entry.get('title', 'No title')
                
                # Get image
                image = extract_image_from_entry(entry, source['category'], title)
                
                # ===== CALCULATE READ TIME =====
                full_text = title + ' ' + summary
                read_time = calculate_read_time(full_text)
                
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
                    'rewritten': False,
                    'read_time': read_time  # ← NEW: Read time in minutes
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
