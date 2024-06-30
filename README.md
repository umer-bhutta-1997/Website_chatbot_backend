# AgriSmart Chatbot

AgriSmart Chatbot is an intelligent chatbot application designed to provide quick and friendly answers to users by leveraging information from previous users of [AgTalk](https://newagtalk.com/category-view.asp).

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the required packages.

```bash
pip install -r requirements.txt
```

## Usage

After installing the required modules, you can run the application with the following command:

```bash
python app.py
```

## Technologies Used

- **Database**: PostgreSQL
- **Vector Store**: Elasticsearch
- **Web Scraping**: Scrapy and Beautiful Soup

## Web Scraper

AgriSmart Chatbot uses a web scraper to extract data from AgTalk. The scraper is built using a combination of Scrapy and Beautiful Soup to efficiently gather and index ads and other relevant information from the website into Elasticsearch.

This chatbot application is configured to run in a local environment. Once set up, it will be ready to help users find answers efficiently.

For any additional details or configurations, please refer to the respective documentation for PostgreSQL, Elasticsearch, Scrapy, and Beautiful Soup.
