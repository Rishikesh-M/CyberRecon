from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup as bs
import pandas as pd

app = Flask(__name__)

social_media_sites = {
    "Instagram": {
        "url": "https://instagram.com/{}",
        "not_found_text": "Page Not Found",
        "alt_not_found_text": "The link you followed may be broken",
        "scrape_logic": {
            "bio": lambda soup: soup.find('meta', property='og:description')['content'] if soup.find('meta', property='og:description') else 'Not Found',
            "profile_pic": lambda soup: soup.find('meta', property='og:image')['content'] if soup.find('meta', property='og:image') else 'Not Found',
        }
    },
    "Github": {
        "url": "https://github.com/{}",
        "not_found_text": "page not found",
        "alt_not_found_text": "user was not found",
        "scrape_logic": {
            "name": lambda soup: soup.find('span', class_='p-name vcard-fullname d-block overflow-hidden').get_text(strip=True) if soup.find('span', class_='p-name vcard-fullname d-block overflow-hidden') else 'Not Found',
            "bio": lambda soup: soup.find('div', class_='p-note user-profile-bio mb-3 js-user-profile-bio').get_text(strip=True) if soup.find('div', class_='p-note user-profile-bio mb-3 js-user-profile-bio') else 'Not Found',
            "followers": lambda soup: soup.find('span', class_='text-bold color-fg-default mr-1').get_text(strip=True) if soup.find('span', class_='text-bold color-fg-default mr-1') else 'Not Found',
        }
    },
    "LinkedIn": {
        "url": "https://linkedin.com/in/{}",
        "not_found_text": "This page doesn’t exist",
        "alt_not_found_text": "We couldn't find the page you're looking for",
        "scrape_logic": {
            "message": lambda soup: 'Scraping LinkedIn is difficult.'
        }
    },
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/osint', methods=['POST'])
def osint():
    username = request.form['username']
    all_data = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36'
    }

    for site, details in social_media_sites.items():
        profile_data = {'Site': site, 'Username': username}
        full_url = details['url'].format(username)
        profile_data['Action'] = full_url  # Store the full URL here

        try:
            response = requests.get(full_url, headers=headers, timeout=5)
            soup = bs(response.text, 'html.parser')
            
            page_content = soup.get_text().lower()
            if details['not_found_text'].lower() in page_content or details['alt_not_found_text'].lower() in page_content:
                profile_data['Status'] = '❌ Not found'
                for key in details['scrape_logic']:
                    profile_data[key] = 'N/A'
            else:
                profile_data['Status'] = '✅ Found'
                for key, func in details['scrape_logic'].items():
                    try:
                        profile_data[key] = func(soup)
                    except Exception as e:
                        profile_data[key] = f"Error scraping: {e}"
            
        except requests.exceptions.RequestException as e:
            profile_data['Status'] = f"❌ Error: {e}"
            for key in details['scrape_logic']:
                profile_data[key] = 'N/A'

        all_data.append(profile_data)

    df = pd.DataFrame(all_data)
    
    def create_button_link(url, status):
        if status == '✅ Found':
            return f'<a href="{url}" target="_blank" class="btn btn-primary btn-sm">Visit Profile</a>'
        return 'N/A'

    df['Action'] = df.apply(lambda row: create_button_link(row['Action'], row['Status']), axis=1)

    html_table = df.to_html(classes=['table', 'table-striped', 'table-dark'], index=False, escape=False)

    return render_template('results.html', username=username, html_table=html_table)

if __name__ == '__main__':
    app.run(debug=True, port=8000)