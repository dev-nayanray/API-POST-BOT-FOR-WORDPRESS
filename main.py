import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# URLs and API
scrape_url = 'https://readforlearn.com/'  # The target website to scrape
api_url = 'https://coupon.wpbestportfoliotheme.top/wp-json/wp/v2/posts'
image_api_url = 'https://coupon.wpbestportfoliotheme.top/wp-json/wp/v2/media'

# Your WordPress authentication token
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL2NvdXBvbi53cGJlc3Rwb3J0Zm9saW90aGVtZS50b3AiLCJpYXQiOjE3MjYyNTQwNzUsIm5iZiI6MTcyNjI1NDA3NSwiZXhwIjoxNzI2ODU4ODc1LCJkYXRhIjp7InVzZXIiOnsiaWQiOiIxIn19fQ.YF-ZPRF6gg_-6zRtLrUNT2yLWFqbaC7fXm9zlRI5pCM"

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# File to store URLs of processed posts (to avoid duplicates)
PROCESSED_POSTS_FILE = 'processed_posts.txt'

# Create the file if it doesn't exist
if not os.path.exists(PROCESSED_POSTS_FILE):
    open(PROCESSED_POSTS_FILE, 'w').close()

def post_exists_in_db(post_url):
    """Check if a post URL has already been processed."""
    with open(PROCESSED_POSTS_FILE, 'r') as file:
        processed_urls = file.read().splitlines()
    return post_url in processed_urls

def save_post_url_to_db(post_url):
    """Save the post URL to the file after processing."""
    with open(PROCESSED_POSTS_FILE, 'a') as file:
        file.write(post_url + '\n')

async def fetch_page(session, url):
    """Fetch a page asynchronously."""
    async with session.get(url) as response:
        if response.status != 200:
            logging.error(f"Failed to fetch {url}, status code: {response.status}")
            return None
        return await response.text()

async def scrape_posts_async(session, url):
    """Scrape posts asynchronously."""
    html_content = await fetch_page(session, url)
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    posts = []
    
    for post in soup.find_all('article'):  # Adjust the tag based on your target site
        post_data = get_post_data(post)
        if post_data and not post_exists_in_db(post_data['link']):
            posts.append(post_data)
    
    return posts

def get_post_data(post):
    """Extract data from a post element."""
    try:
        title = post.find('h2').get_text(strip=True)
        link = post.find('a')['href']
        description = post.find('p').get_text(strip=True)
        image_url = post.find('img')['src'] if post.find('img') else None  # Handle image if available
        return {
            'title': title,
            'link': link,
            'description': description,
            'image_url': image_url
        }
    except AttributeError as e:
        logging.error(f"Error extracting post data: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

async def upload_image_to_wp_async(session, image_url):
    """Upload an image to WordPress asynchronously and return the image ID."""
    try:
        async with session.get(image_url) as image_response:
            image_data = await image_response.read()
            filename = image_url.split('/')[-1]

            files = {
                'file': (filename, image_data),
            }

            async with session.post(image_api_url, headers=headers, data=image_data) as response:
                if response.status == 201:
                    image_info = await response.json()
                    return image_info.get('id')
                else:
                    logging.error(f"Failed to upload image from '{image_url}', status code: {response.status}")
                    return None
    except Exception as e:
        logging.error(f"Error uploading image: {e}")
        return None

async def create_wp_post_async(session, post_data):
    """Create a WordPress post asynchronously."""
    if post_exists_in_db(post_data['link']):
        logging.info(f"Post '{post_data['title']}' already exists. Skipping.")
        return

    # Upload the featured image if available
    image_id = await upload_image_to_wp_async(session, post_data['image_url']) if post_data.get('image_url') else None
    
    data = {
        'title': post_data['title'],
        'content': post_data['description'],
        'status': 'publish',
        'featured_media': image_id  # Attach the uploaded image if available
    }
    
    async with session.post(api_url, headers=headers, json=data) as response:
        if response.status == 201:
            logging.info(f"Post '{post_data['title']}' created successfully!")
            save_post_url_to_db(post_data['link'])  # Save the post URL to avoid duplicates
        else:
            logging.error(f"Failed to create post '{post_data['title']}', status code: {response.status}")
            logging.error(await response.text())

async def scrape_paginated_posts(session, base_url, max_pages=5):
    """Scrape posts from paginated pages asynchronously."""
    all_posts = []
    for page in range(1, max_pages + 1):
        page_url = f"{base_url}/page/{page}/"
        logging.info(f"Scraping page {page}: {page_url}")
        
        posts = await scrape_posts_async(session, page_url)
        if not posts:
            logging.info(f"No more posts found on page {page}. Stopping pagination.")
            break
        
        all_posts.extend(posts)
    
    return all_posts

async def main_async(scrape_url, max_pages=5):
    """Main asynchronous function to scrape and post automatically."""
    async with aiohttp.ClientSession() as session:
        posts = await scrape_paginated_posts(session, scrape_url, max_pages=max_pages)
        
        if posts:
            tasks = [create_wp_post_async(session, post) for post in posts]
            await asyncio.gather(*tasks)
        else:
            logging.info("No posts found to scrape.")

# Run the asynchronous process
asyncio.run(main_async(scrape_url, max_pages=50))
