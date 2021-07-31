import requests
from pyquery import PyQuery as pq
import urllib
import time
import json
import os
import re
import random
from datetime import datetime

class Configuration:
    def __init__(self, file_name):
        with open(file_name, encoding="utf-8") as json_file:  
            self._data = json.load(json_file)

    def keywords(self):
        return self._data["keywords"]
    
    def promotion_criterias(self):
        return self._data["criterias"]

class LogWriter:
    def __init__(self, file_name):
        self._file_name = file_name
        if os.path.isfile(file_name):
            os.remove(file_name)
    
    def write(self, msg):
        now = datetime.now()
        time_str = date_time = now.strftime("%Y/%m/%d %H:%M:%S")
        whole_line = time_str + " " + msg
        print(whole_line)

        with open(self._file_name, "a", encoding="utf-8") as f:
            f.write(whole_line + "\n")

class Output:
    def __init__(self, file_name):
        self._file_name = file_name
        if os.path.isfile(file_name):
            os.remove(file_name)
    
    def write(self, promotion):
        now = datetime.now()
        time_str = date_time = now.strftime("%Y/%m/%d %H:%M:%S")

        with open(self._file_name, "a", encoding="utf-8") as f:
            f.write(time_str + "\n")
            f.write(promotion["title"] + "\n")
            f.write(promotion["url"] + "\n")

            if "items" in promotion:
                for item in promotion["items"]:
                    f.write(item["title"] + "\n")

            f.write("\n")

class MySession:
    def __init__(self, log):
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"
        ]

        self._session = requests.Session()
        self._retry_limit = 10
        self._log = log

    def _default_header(self):
        return { "User-Agent": self._user_agents[random.randint(0, len(self._user_agents) - 1)] }

    def get(self, url):
        headers = self._default_header()

        for i in range(self._retry_limit):
            try:
                self._log.write(url + " trial[" + str(i + 1) + "]")
                r = self._session.get(url, headers = headers)
                return r
            except:
                time.sleep(i + 1)

class Engine():
    def __init__(self):
        self._config = Configuration("config.json")
        self._log = LogWriter("log.txt")
        self._output = Output("match.txt")
        self._output_unmatch = Output("unmatch.txt")
        self._avoid_login_limit = 10
        self._reset_session()

    def _reset_session(self):
        self._session = MySession(self._log)

    def _dump_html(self, file_name, html):
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(html)

    def run(self):
        initial_keywords = self._config.keywords()
        promo_criterias = self._config.promotion_criterias()

        promotion_ids = {}
        processed_item_ids = {}

        random.shuffle(initial_keywords)

        for keyword in initial_keywords:
            self._reset_session()
            self._log.write(keyword)

            offset = 0
            page = 1
            while page < 10:
                #search
                url = "https://search.jd.com/Search?keyword=" + urllib.parse.quote_plus(keyword)
                if page > 1:
                    url += "&s=" + str(offset + 1) + "&page=" + str(page)
                
                items_on_page = self._get_items_by_search_url(url)
                if len(items_on_page) == 0:
                    #self._dump_html(keyword + "-" + str(page) + ".html", r.text)
                    break
                offset += len(items_on_page)
                page += 1

                #get promotions
                for item in items_on_page:
                    #random
                    if random.randint(0, 3) == 0:
                        continue

                    if item["id"] in processed_item_ids:
                        continue

                    self._log.write(item["id"] + " " + item["title"])

                    try:
                        promotions_on_item = self._get_promotions(item)
                    except:
                        self._log.write("blocked? slow down a bit")
                        time.sleep(random.randint(60, 120))
                        continue

                    processed_item_ids[item["id"]] = True

                    for promotion in promotions_on_item:
                        if len(promotion["id"]) == 0 or promotion["id"] in promotion_ids:
                            continue

                        self._log.write("> " + promotion["id"] + " " + promotion["title"])
                        promotion_ids[promotion["id"]] = True

                        found = False
                        for criteria in promo_criterias:
                            if criteria in promotion["title"]:
                                found = True
                                break

                        if not found:
                            found = self._check_fulfil_deduct_pattern(promotion["title"])

                        if not found:
                            self._output_unmatch.write(promotion)
                            continue

                        promotion["items"] = self._get_items_in_promotion(promotion["url"], 200)

                        self._output.write(promotion)
                    
                    time.sleep(random.randint(5, 35))

    def _get_items_in_promotion(self, promotion_url, max_count):
        lst = []
        page = 1
        offset = 0
        while True:
            url = promotion_url
            if page > 1:
                url += "&s=" + str(offset + 1) + "&page=" + str(page)

            items_on_page = self._get_items_by_search_url(url)
            offset += len(items_on_page)
            page += 1

            if len(items_on_page) == 0:
                break

            for item in items_on_page:
                lst.append(item)
                if max_count is not None and len(lst) >= max_count:
                    break

            if max_count is not None and len(lst) >= max_count:
                break
        
        return lst


    def _get_items_by_search_url(self, search_url):
        for trial in range(self._avoid_login_limit):
            r = self._session.get(search_url)
            if not self._is_login_page(r.text):
                break
            self._log.write("login page is shown, try again")
            self._reset_session()
            time.sleep(random.randint(60, 180))

        return self._collect_items_from_search_result(r.text)

    def _is_login_page(self, html):
        dom = pq(html)
        return len(dom("#formlogin")) > 0

    def _get_promotions(self, item):
        lst = []
        url = "https://item-soa.jd.com/getWareBusiness?skuId=" + item["id"] + "&shopId=" + item["shop"]["id"] + "&venderId=" + item["shop"]["id"] + "&num=1"

        json_text = self._session.get(url).text
        obj = json.loads(json_text)

        for activity in obj["promotion"]["activity"]:
            promoid = activity["promoId"]
            title = activity["value"]
            promotion_url = "https://search.jd.com/Search?activity_id=" + promoid
            lst.append({ "id": promoid, "title": title, "url": promotion_url })
        
        return lst

    def _collect_items_from_search_result(self, html):
        lst = []
        dom = pq(html)
        lis = dom("#J_goodsList li.gl-item")
        for li in lis:
            id = li.attrib["data-sku"]
            
            title = pq(li).find(".p-name em").text().replace("\n", " ")

            shop_anchor = pq(li).find(".p-shop a")
            onclick = shop_anchor.attr("onclick")  #searchlog(1,'1000281326',0,58)
            if onclick is None:
                continue
            shop_id = onclick.split(",")[1].strip("'")
            shop_name = shop_anchor.text()

            lst.append({ "id": id, "title": title, "shop": { "id": shop_id, "name": shop_name } })
        return lst

    def _check_fulfil_deduct_pattern(self, promotion_title):
        patterns = [ "满[0-9]+元减[0-9]+元", "每满[0-9]+元，可减[0-9]+元现金" ]

        for pattern in patterns:
            txts = re.findall(pattern, promotion_title)

            if txts is not None and len(txts) > 0:
                for txt in txts:
                    match = re.match(pattern, txt)
                    for reg in match.regs:
                        tokens = re.findall("[0-9]+", txt)
                        fulfil = int(tokens[0])
                        deduct = int(tokens[1])
                        if deduct * 2 >= fulfil:
                            return True

        return False

if __name__ == "__main__":
    Engine().run()
