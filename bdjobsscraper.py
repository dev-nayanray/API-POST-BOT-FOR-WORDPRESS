import requests
from bs4 import BeautifulSoup
import json
import logging

# Set up logging
logging.basicConfig(filename='scrape_and_post.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# URL of the website to scrape
scrape_url = 'https://readforlearn.com/'

# WordPress site API endpoint for creating posts
api_url = 'https://coupon.wpbestportfoliotheme.top/wp-json/wp/v2/posts'

# WordPress site API endpoint for media (used for uploading images)
media_api_url = 'https://coupon.wpbestportfoliotheme.top/wp-json/wp/v2/media'

# Your authentication token
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL2NvdXBvbi53cGJlc3Rwb3J0Zm9saW90aGVtZS50b3AiLCJpYXQiOjE3MjYyNTQwNzUsIm5iZiI6MTcyNjI1NDA3NSwiZXhwIjoxNzI2ODU4ODc1LCJkYXRhIjp7InVzZXIiOnsiaWQiOiIxIn19fQ.YF-ZPRF6gg_-6zRtLrUNT2yLWFqbaC7fXm9zlRI5pCM"

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

def upload_image(image_url):
    """Upload image to WordPress and return the image ID."""
    try:
        image_data = requests.get(image_url).content
        filename = image_url.split('/')[-1]

        media_headers = headers.copy()
        media_headers['Content-Disposition'] = f'attachment; filename={filename}'
        media_headers['Content-Type'] = 'image/jpeg'  # Adjust this if not a jpeg

        media_response = requests.post(media_api_url, headers=media_headers, data=image_data)
        
        if media_response.status_code == 201:
            media_id = media_response.json().get('id')
            return media_id
        else:
            logging.error(f"Failed to upload image. Status code: {media_response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error uploading image: {e}")
        return None

def get_post_data(post):
    """Extract data from a post element, including category, tags, and image."""
    try:
        title = post.find('h2').get_text(strip=True)
        link = post.find('a')['href']
        description = post.find('p').get_text(strip=True)
        
        # Assume categories and tags are part of post (adapt if needed)
        categories = [cat.get_text(strip=True) for cat in post.find_all('a', class_='category')]  # Example
        tags = [tag.get_text(strip=True) for tag in post.find_all('a', class_='tag')]  # Example
        
        # Get the image (if available)
        image_url = post.find('img')['src'] if post.find('img') else None

        return {
            'title': title,
            'link': link,
            'description': description,
            'categories': categories,
            'tags': tags,
            'image_url': image_url
        }
    except AttributeError as e:
        logging.error(f"Error extracting post data: {e}")
        return None

def scrape_posts(url):
    """Scrape posts from the website."""
    response = requests.get(url)
    
    if response.status_code != 200:
        logging.error(f"Failed to retrieve content, status code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    posts = []

    # Find all post elements, update 'article' based on actual tag structure
    for post in soup.find_all('article'):
        post_data = get_post_data(post)
        if post_data:
            posts.append(post_data)

    return posts

def post_exists(title):
    """Check if a post with the same title already exists in WordPress."""
    search_url = f"{api_url}?search={title}"
    response = requests.get(search_url, headers=headers)
    
    if response.status_code == 200:
        posts = response.json()
        return any(post['title']['rendered'] == title for post in posts)
    logging.error(f"Failed to check existing posts, status code: {response.status_code}")
    return False

def create_wp_post(post_data):
    """Create a WordPress post via the REST API, including categories, tags, and featured image."""
    if post_exists(post_data['title']):
        logging.info(f"Post '{post_data['title']}' already exists. Skipping.")
        return

    # Upload the image and get the image ID
    image_id = upload_image(post_data['image_url']) if post_data['image_url'] else None

    # Prepare the payload
    data = {
        'title': post_data['title'],
        'content': post_data['description'],
        'status': 'publish',  # Automatically publish the post
        'categories': post_data['categories'],  # Include categories
        'tags': post_data['tags'],  # Include tags
        'featured_media': image_id  # Include image ID if available
    }
    
    response = requests.post(api_url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 201:
        logging.info(f"Post '{post_data['title']}' created successfully!")
    else:
        logging.error(f"Failed to create post '{post_data['title']}', status code: {response.status_code}")
        logging.error(response.text)

def scrape_all_pages(base_url):
    """Scrape all pages from the website by handling pagination."""
    page_number = 1
    while True:
        url = f"{base_url}/page/{page_number}/"
        posts = scrape_posts(url)
        
        if not posts:
            logging.info(f"No posts found on page {page_number}. Stopping pagination.")
            break
        
        for post in posts:
            create_wp_post(post)
        
        page_number += 1

def auto_scrape_and_post(scrape_url):
    """Scrape the posts and create WordPress posts automatically."""
    scrape_all_pages(scrape_url)

# Start the scraping and posting process
auto_scrape_and_post(scrape_url)
