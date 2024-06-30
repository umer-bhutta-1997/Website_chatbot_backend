import subprocess
import json
import re

def run_scraper(start_date, end_date, page):
    command = f'scrapy crawl machine_spider -a start_date={start_date} -a end_date={end_date} -a page={page} -O test_1.json'
    try:
        subprocess.run(command, shell=True, check=True)
        print("Command executed successfully.")
    except subprocess.CalledProcessError as e:
        print("Error executing command:", e)