import requests as r
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import bs4 as bparse
from flask import Flask, request, jsonify, after_this_request, send_file
from flask_cors import CORS
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://perpus-sederhana.vercel.app/"}})
api_keys = {
    'key': '5ehadi'
}

def verify_api_key(api_key):
    return api_key in api_keys.values()

def scrape(search_text):
    url = "https://www.pdfdrive.com/search"
    query_params = {
        "q": search_text,
        "more": "true"
    }

    headers_search = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
    }

    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session = r.Session()
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update(headers_search)

    try:
        response = session.get(url, headers=headers_search, params=query_params, timeout=60)
        response.raise_for_status()
    except r.RequestException as e:
        print(f"Request error: {e}")
        return None

    soup = bparse.BeautifulSoup(response.text, 'html.parser')
    books = soup.find_all('div', class_='file-left')
    book_list = []

    def scrape_book_details(book):
        nonlocal book_count
        book_data = {}
        if book_count >= 10:
            return None

        img_element = book.find('img', class_='img-zoom file-img')
        if img_element:
            book_data['image_url'] = img_element['data-original']

        url_element = book.find('a', href=True)
        if url_element:
            full_book_url = urljoin(url, url_element['href'])
            book_data['book_url'] = full_book_url

            try:
                response_book = session.get(full_book_url, headers=headers_search, timeout=60)
                response_book.raise_for_status()

                book_soup = bparse.BeautifulSoup(response_book.text, 'html.parser')
                title_element = book_soup.find('h1', class_='ebook-title')
                if title_element:
                    book_data['title'] = title_element.get_text(strip=True)

                description_element = book_soup.find('div', class_='quotes')
                if description_element:
                    book_data['quote'] = description_element.get_text(strip=True)

                file_right = book_soup.find('div', class_='file-right')
                if file_right:
                    info_elements = file_right.find_all('span')
                    for info in info_elements:
                        if 'fi-pagecount' in info['class']:
                            book_data['page_count'] = info.get_text(strip=True)
                        elif 'fi-year' in info['class']:
                            book_data['year'] = info.get_text(strip=True)
                        elif 'fi-size' in info['class']:
                            book_data['size'] = info.get_text(strip=True)
                        elif 'fi-lang' in info['class']:
                            book_data['language'] = info.get_text(strip=True)

            except r.RequestException as e:
                print(f"Request error: {e}")
                return None

            book_count += 1

        return book_data

    book_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scrape_book_details, book) for book in books]
        for future in as_completed(futures):
            book_data = future.result()
            if book_data:
                book_list.append(book_data)

                if len(book_list) >= 10:
                    break

    return book_list

@app.route('/api/book/search', methods=['POST'])
def api_search():
    search_text = request.form.get('text')
    api_key = request.form.get('key')

    if not api_key or not verify_api_key(api_key):
        return jsonify({'error': 'Unauthorized', 'message': 'Invalid API key'}), 401

    if not search_text:
        return jsonify({'error': 'Parameter "text" is required'}), 400

    result = scrape(search_text)
    if result is not None:
        response = jsonify(result)
        @after_this_request
        def add_header(response):
            response.headers['Access-Control-Allow-Origin'] = 'https://perpus-sederhana.vercel.app'
            response.headers['Access-Control-Allow-Methods'] = 'POST'
            return response
        return response, 200
    else:
        return jsonify({'error': 'Failed to fetch data'}), 500

@app.route('/api/book', methods=['GET'])
def book_api():
    return jsonify({
        'author': 'Hadiani',
        'message': 'This API Free Book Database'
    }), 200

@app.route('/api', methods=['GET'])
def api_welcome():
    return jsonify({
        'author': 'Hadiani',
        'message': 'selamat datang di api hadiani'
    }), 200

@app.route('/')
def mywebsite():
    return send_file('index.html')
    

if __name__ == '__main__':
    app.run(debug=True, port=3000)
