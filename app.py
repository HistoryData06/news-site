from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import re
from datetime import datetime
import random
import os
from bs4 import BeautifulSoup
import feedparser

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

def generate_fallback_article(title, year):
    year_text = f" in {year}" if year else ""
    article = f"{title} is a significant historical event{year_text} that represents an important moment in history. "
    if year:
        article += f"The year {year} was a period of great change and development, and this event played a crucial role in shaping the world we live in today. "
    article += "Historians continue to study this event to understand its causes, consequences, and lasting impact on society. "
    article += "Understanding this event requires looking at the broader historical context. The political, social, and economic conditions of the time created the environment in which this event could occur. "
    article += "This event is significant because it influenced subsequent historical developments and shaped the course of history. Its legacy can still be seen in modern institutions, cultural practices, and international relations. "
    article += "The lasting impact of this event serves as a reminder of how historical moments continue to influence our present and future. By studying such events, we gain valuable insights into human nature, society, and the forces that shape our world."
    return article

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

@app.route('/api/article')
def get_article():
    """Generate a clean, plain text article (200-300 words)"""
    title = request.args.get('title', '')
    if not title:
        return jsonify({'error': 'No title provided'}), 400
    
    year_match = re.search(r'\b(\d{4})\b', title)
    year = year_match.group(1) if year_match else None
    
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    
    if deepseek_key:
        try:
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {deepseek_key}",
                "Content-Type": "application/json"
            }
            
            year_text = f" in the year {year}" if year else ""
            
            prompt = f"""Write a complete, self-contained news article about: {title}{year_text}.

IMPORTANT:
- Write as a normal news article, just plain text
- NO headings like "Historical Context", "Significance", "Legacy"
- NO bullet points or asterisks
- NO markdown formatting at all
- Just flowing paragraphs like a real news story
- Be 200-300 words long
- Include key facts and context
- End with a natural conclusion
- Write in English

Article:"""
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a professional journalist writing engaging, clear news articles without any headings, bullet points, or markdown formatting. Just plain text paragraphs."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                article = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                if article and len(article) > 50:
                    article = re.sub(r'\*\*([^*]+)\*\*', r'\1', article)
                    article = re.sub(r'#{1,6}\s*', '', article)
                    article = re.sub(r'[-*]\s+', '', article)
                    return jsonify({
                        'title': title,
                        'content': article,
                        'source': 'ai_generated',
                        'word_count': len(article.split())
                    })
        except Exception as e:
            print(f"DeepSeek error: {e}")
    
    fallback = generate_fallback_article(title, year)
    return jsonify({
        'title': title,
        'content': fallback,
        'source': 'fallback',
        'word_count': len(fallback.split())
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'News API is running!'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
