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
        self._promotions = {}
        self._is_ended = False
    
    def get_file_name(self):
        return self._file_name

    def _update_promotion_update_time(self, promotion_id):
        self._promotions[promotion_id]["time"] = datetime.now()

    def add_item(self, promotion_id, item):
        if promotion_id not in self._promotions:
            return

        if "items" not in self._promotions[promotion_id]:
            self._promotions[promotion_id]["items"] = []

        self._promotions[promotion_id]["items"].append(item)
        self._update_promotion_update_time(promotion_id)

    def add_promotion(self, promotion):
        self._promotions[promotion["id"]] = promotion
        self._update_promotion_update_time(promotion["id"])

    def complete(self):
        self._is_ended = True
        self.flush()

    def flush_csv(self):
        with open(self._file_name, "w", encoding="utf-8") as f:
            f.write("活動")
            f.write(",")
            f.write("活動 ID")
            f.write(",")
            f.write("產品")
            f.write(",")
            f.write("售往海外")
            f.write(",")
            f.write("網址")
            f.write(",")
            f.write("\n")

            for promotion_id in self._promotions:
                write_promotion = self._promotions[promotion_id]
                time_str = write_promotion["time"].strftime("%Y/%m/%d %H:%M:%S")

                if "items" in write_promotion:
                    for item in write_promotion["items"]:
                        #if not item["isSoldOversea"]:
                        #    continue

                        f.write(write_promotion["title"].replace(",", "/").replace("，", "/"))
                        f.write(",")
                        
                        f.write(write_promotion["id"])
                        f.write(",")
                        
                        f.write(item["title"].replace(",", "/").replace("，", "/"))
                        f.write(",")
                        
                        if item["isSoldOversea"]:
                            f.write("Y")
                        else:
                            f.write("")
                        f.write(",")

                        f.write("https://item.jd.com/" + item["id"] + ".html")

                        f.write("\n")
            
            if self._is_ended:
                f.write("EOF\n")

    def flush(self):
        with open(self._file_name, "w", encoding="utf-8") as f:
            for promotion_id in self._promotions:
                write_promotion = self._promotions[promotion_id]

                count = 0
                if "items" in write_promotion:
                    for item in write_promotion["items"]:
                        if not item["isSoldOversea"]:
                            count += 1

                if count == 0:
                    continue
                
                time_str = write_promotion["time"].strftime("%Y/%m/%d %H:%M:%S")

                f.write(time_str + "\n")
                f.write(write_promotion["title"] + "\n")
                f.write(write_promotion["url"] + "\n")

                if "items" in write_promotion:
                    for item in write_promotion["items"]:
                        if not item["isSoldOversea"]:
                            continue
                        f.write(item["title"] + " " + "https://item.jd.com/" + item["id"] + ".html" + "\n")

                f.write("\n")
            
            if self._is_ended:
                f.write("EOF\n")

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

from GoogleServices import GoogleServices
from googleapiclient.http import MediaFileUpload

class ResultUploader:
    def __init__(self, tag):
        if os.path.isfile("credentials.json"):
            google = GoogleServices()
            self._drive = google.get_drive_service()
        else:
            self._drive = None
        self._tag = tag
        self._folder_id = None
        self._file_id = None
    
    def upload(self, file_name):
        if self._drive is None:
            return False

        if self._folder_id is None:
            self._folder_id = self._get_id_of_JD_folder()
        self._file_id = self._upload_task(self._folder_id, file_name, "JD" + self._tag + ".txt", self._file_id)

        return True

    def _upload_task(self, folder_id, local_file_name, upload_file_name, file_id):
        file_metadata = {
            "name": upload_file_name,
            "mimeType": "text/plain"
        }

        media = MediaFileUpload(local_file_name, mimetype="text/plain")

        if file_id is not None:
            file = self._drive.files().update(fileId = file_id, body=file_metadata, media_body=media, fields='id').execute()
        else:
            file_metadata["parents"] = [ folder_id ]
            file = self._drive.files().create(body=file_metadata, media_body=media, fields='id').execute()

        return file["id"]

    def _get_id_of_JD_folder(self):
        results = self._drive.files().list(
            fields="files(id)",
            q="mimeType='application/vnd.google-apps.folder' and name='JD' and trashed=false").execute()
        items = results.get("files", [])
        if len(items) == 0:
            raise ValueError("JD folder is not found")
        folder_id = items[0].get("id")
        return folder_id

class Engine():
    def __init__(self):
        self._config = Configuration("config.json")
        self._log = LogWriter("log.txt")
        self._output = Output("match.txt")
        self._output_unmatch = Output("unmatch.txt")
        self._avoid_login_limit = 10
        self._reset_session()
        self._result_uploader = ResultUploader(datetime.now().strftime("%Y%m%dT%H%M%S"))

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
            while page < 20:
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
                    if random.randint(1, 10) <= 2:
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
                        if len(promotion["id"]) == 0:
                            continue

                        if promotion["id"] in promotion_ids:
                            self._output.add_item(promotion["id"], item)
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
                            found = self._check_discount_pattern(promotion["title"])

                        if not found:
                            self._output_unmatch.add_promotion(promotion)
                            self._output_unmatch.flush()
                            continue

                        #promotion["items"] = self._get_items_in_promotion(promotion["url"], 200)

                        self._output.add_promotion(promotion)
                        self._output.add_item(promotion["id"], item)
                        self._output.flush()

                        if os.path.isfile(self._output.get_file_name()):
                            self._result_uploader.upload(self._output.get_file_name())

                    time.sleep(random.randint(0, 2))
        
                time.sleep(random.randint(10, 50))

        self._output.complete()

        if os.path.isfile(self._output.get_file_name()):
            self._result_uploader.upload(self._output.get_file_name())

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

            time.sleep(random.randint(5, 35))
        
        return lst


    def _get_items_by_search_url(self, search_url):
        for trial in range(self._avoid_login_limit):
            r = self._session.get(search_url)
            if not self._is_login_page(r.text):
                break
            self._log.write("login page is shown, try again")
            self._reset_session()
            time.sleep(random.randint(10, 30))

        return self._collect_items_from_search_result(r.text)

    def _is_login_page(self, html):
        dom = pq(html)
        return len(dom("#formlogin")) > 0

    def _get_promotions(self, item):
        lst = []
        url = "https://item-soa.jd.com/getWareBusiness?skuId=" + item["id"] + "&shopId=" + item["shop"]["id"] + "&venderId=" + item["shop"]["id"] + "&num=1"

        json_text = self._session.get(url).text
        obj = json.loads(json_text)

        item["isSoldOversea"] = "soldOversea" in obj and "isSoldOversea" in obj["soldOversea"] and obj["soldOversea"]["isSoldOversea"] == True

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

    def _check_discount_pattern(self, promotion_title):
        patterns = [ "(总价打(([0-9]+[.])?[0-9]+)折)" ]

        for pattern in patterns:
            txt_or_tuples = re.findall(pattern, promotion_title)

            if txt_or_tuples is not None and len(txt_or_tuples) > 0:
                 for txt_or_tuple in txt_or_tuples:
                    if type(txt_or_tuple) == "string":
                        txt = txt_or_tuple
                    else:
                        txt = txt_or_tuple[0]

                    match = re.match(pattern, txt)
                    for reg in match.regs:
                        num_matches = re.findall("(([0-9]+\.)?[0-9]+)", txt)
                        for num_match in num_matches:
                            if type(num_match) == "string":
                                num = num_match
                            else:
                                num = num_match[0]
                            rate = float(num)
                            if rate <= 5:
                                return True
                            break   #need the longest match only
                        break   #need the longest match only
                    
                    break   #need the longest match only

        return False

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
