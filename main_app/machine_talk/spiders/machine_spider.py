from datetime import datetime
import scrapy
from scrapy import Request
import re
from elastic_search import data_to_elasticSearch

class MachineSpiderSpider(scrapy.Spider):
    name = "machine_spider"
    allowed_domains = ["newagtalk.com"]
    # start_urls = ["https://newagtalk.com/forums/forum-view.asp?fid=2&bookmark=1&displaytype=flat"]
    def __init__(self, start_date, end_date, page, **kwargs):
        date_format = "%m/%d/%Y"
        start_datetime_obj = datetime.strptime(start_date, date_format)
        start_date_only = start_datetime_obj.date()
        self.start_date = start_date_only  # py36
        end_datetime_obj = datetime.strptime(end_date, date_format)
        end_date_only = end_datetime_obj.date()
        self.end_date = end_date_only
        self.page_name = int(page)
        super().__init__(**kwargs)  # python3
    
    def start_requests(self):
        """
        This is to select the page this is to be scrapped
        """
        if self.page_name == 1:
            # Machine Talk
            url = "https://newagtalk.com/forums/forum-view.asp?fid=2&bookmark=1&displaytype=flat"
        elif self.page_name == 2:
            # Drone Talk
            url = "https://newagtalk.com/forums/forum-view.asp?fid=17&bookmark=1&displaytype=flat"
        elif self.page_name == 3:
            # Crop Talk
            url = "https://newagtalk.com/forums/forum-view.asp?fid=3&bookmark=1&displaytype=flat"
        elif self.page_name == 4:
            # Precision Talk 
            url = "https://newagtalk.com/forums/forum-view.asp?fid=6&bookmark=1&displaytype=flat"
        
        yield Request(url = url, callback = self.parse)

    def parse(self, response):

        items = response.xpath('//table[@class="bbstable"]//tr')

        for item in items:
            date = item.css('td.messagecellbody2.smalltext::text').get()
            if date is not None:
                date = date.split(": ")[1]
                date_format = "%m/%d/%Y %H:%M"
                datetime_obj = datetime.strptime(date, date_format)
                date_only = datetime_obj.date()
                if self.start_date <= date_only <= self.end_date:
                    data = {
                        "link": item.css('a.threadlink::attr(href)').get(),
                        "Title": item.css('a.threadlink::text').get()
                    }
                    if data["link"]:
                        yield response.follow(data["link"], callback=self.parse_question_link)
                else:
                    pass
        

        # Iterate over next page URLs
        if self.page_name == 1:
            # Machine Talk
            for x in range(1, 15005, 50):
                url = "https://newagtalk.com/forums/forum-view.asp?fid=2&bookmark={}&displaytype=flat".format(x)
                yield response.follow(url, callback=self.parse)
        elif self.page_name == 2:
            # Drone Talk
            for x in range(1, 15005, 50):
                url = "https://newagtalk.com/forums/forum-view.asp?fid=17&bookmark={}&displaytype=flat".format(x)
                yield response.follow(url, callback=self.parse)
        elif self.page_name == 3:
            # Crop Talk
            for x in range(1, 15005, 50):
                url = "https://newagtalk.com/forums/forum-view.asp?fid=3&bookmark={}&displaytype=flat".format(x)
                yield response.follow(url, callback=self.parse)

        elif self.page_name == 4:
            # Precision Talk 
            for x in range(1, 15005, 50):
                url = "https://newagtalk.com/forums/forum-view.asp?fid=6&bookmark={}&displaytype=flat".format(x)
                yield response.follow(url, callback=self.parse)

        

    def parse_question_link(self, response):
        self.logger.info("Got successful response from {}".format(response.url))
        if response.css('p').getall() != []:
            question = response.css('p').getall()
        else:
            question = response.css('td.messagemiddle:nth-child(2)::text').getall()
        table = response.xpath('//html//body//table[3]//ul')
        td = table.css('ul')[0]
        data = {
            "question":  question,
            "link": td.css('a.threadlink::attr(href)').getall()
        }
        data["link"].pop(0)
        results = {}  # Create an empty list to store the results
        if data["link"]:
            for link in data["link"]:
                yield response.follow(link, callback=self.parse_answer_link, cb_kwargs=dict(question=data["question"], results=results, length=len(data['link'])))
        else:
            yield {
                "question": question,
                "reply": []
            }

    def parse_answer_link(self, response, question, results, length):
        self.logger.info("Got successful response from {}".format(response.url))
        if response.css('p').getall() != []:
            answer = response.css('p').getall()
        else:
            answer = response.css('td.messagemiddle:nth-child(2)::text').getall()
            answer = [re.sub('<.*?>', '', ans) for ans in answer]
            answer = " ".join(answer)
        table = response.xpath('//html//body//table[3]//ul')
        td = table.css('ul')[0]
        if "question" in results.keys():
            pass
        else:
            results['question'] = question
        if "reply" in results.keys():
            if type(answer) == str:
                results["reply"].append(answer)  # Append the data to the results list
            else:
                results["reply"].append(answer[0])
        else:
            if type(answer) == str:
                results["reply"] = [answer]
            else: 
                results["reply"] = [answer[0]]
        if len(results['reply']) == length:
            d = results
            if d['question'] != [] and d['reply'] != []:
                d['reply'] = [re.sub(r'<[^>]+>|<\/?p>', '', x).replace("\r\n", "").strip() for x in d['reply']]
                d['question'] = " ".join([re.sub(r'<[^>]+>|<\/?p>', '', x).replace("<p>", "").replace("\r\n", "").strip() for x in d['question']])
                d['reply'] = '\n'.join([f"{data}" for count, data in enumerate(d['reply'], 1)])
                if d['question'] != [] and d['reply'] != []:
                    data_to_elasticSearch(d['question'], d['reply'])
                    print("----------------------- DATA ADDED TO ELASTICSEARCH")
            yield results
    


        
