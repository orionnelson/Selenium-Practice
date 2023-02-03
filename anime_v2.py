import os
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as Firefox_Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import requests
from tqdm.auto import tqdm
import zipfile
import concurrent.futures
from tqdm.contrib.concurrent import process_map
import multiprocessing
from multiprocessing import current_process
import random
import pickle
import configparser
import sys
default =  configparser.ConfigParser()
default.read('settings.cfg')
FIND_DUB_FIRST = default["DEFAULT"]["Dub"] =='yes'
DEBUG = default["DEFAULT"]["Debug"] =='yes'
FIND_DUB_FIRST = True
DEBUG = False
fb_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
geo_path = os.path.join(os.path.dirname(__file__),"geckodriver.exe")
serv = Service(geo_path)
firefox_options = Firefox_Options()
firefox_options.binary = fb_path
firefox_options.set_preference("dom.push.enabled", False)
firefox_options.set_preference("browser.sessionstore.postdata", False)
firefox_options.set_preference("dom.disable_beforeunload", True)
firefox_options.set_preference("dom.confirm_repost.testing.always_accept", True)
anime_url_base="https://4anime.gg"

from multiprocessing import Process, Value, Lock

# Changes Needed
# - On Failing to find a video url it will add it to a temp file and on next run it will try to complete the temp file first
# - It will load objects backwards starting from the latest episode and working backwards until it reaches the last seen episode

def getcwdir():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)
    return application_path
    


def getLocalPath(f):
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)
    return os.path.join(application_path,f)
    


class Counter(object):
    def __init__(self, initval=0):
        self.val = Value('i', initval)
        self.lock = Lock()

    def increment(self):
        with self.lock:
            self.val.value += 1

    def value(self):
        with self.lock:
            return self.val.value


tqdm_count = Counter()



def close_any_alerts(browser):
    try:
        alert = browser.switch_to.alert
        alert.close()
    except:
        pass


# returns the current shows in episodes.txt as a dict split by showurl:episode
def get_shows():
    with open(getLocalPath('episodes.txt'),'r+') as f:
        shows = f.readlines()
    return {show.split(':')[0]: show.split(':')[-1].strip() for show in shows}

#This Code Below just prevents idiots from using the browser
if os.path.exists(fb_path) is False:
    raise ValueError("The binary path to firefox does not exist.")
browser = None

def get_browser():
    global browser
    # only one instance of a browser opens, remove global for multiple instances
    if not browser:
        browser = webdriver.Firefox(service=serv,options=firefox_options)
    return browser


def get_episodes_from_anime(browser):
        # Counld not find a good
        episodes = browser.find_element('id','episodes-content')
        return episodes

def download_file(path,url,local_filename,lb_pos):
    CHNK_SZ = 8192 * 10
    local_filename = local_filename
    pth = os.path.join(path,local_filename)
    pos = lb_pos
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(pth, 'wb') as f:
            tt = r.headers['Content-length']
            with tqdm(total=int(tt), desc="Downloading "+ str(local_filename),position=pos,leave=False)as pbar:
                    for chunk in r.iter_content(chunk_size=CHNK_SZ): 
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        #if chunk:
                        f.write(chunk)
                        pbar.update(int(CHNK_SZ))
    os.system('cls' if os.name == 'nt' else 'clear')
    return local_filename

def download_subtitles(browser, show, episode, s_path):
    show = show.rsplit('-',1)[0]
    url = "https://www.opensubtitles.org/en/search2?MovieName=%s&action=search&SubLanguageID=eng&Episode=%s" % (show, episode)
    browser.get(url) # bt-dwl-bt
    time.sleep(3)
    dload = browser.find_element('id','bt-dwl-bt')
    link = dload.get_attribute('href')
    r = requests.get(link, stream=True)
    zip_path = os.path.join(s_path,"%s.zip" % episode)
    with open(getLocalPath(zip_path), 'wb' ) as fd:
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        ep_path  = "%s/%s" % (s_path,episode)
        os.mkdir(ep_path)
        zip_ref.extractall(ep_path)
    os.remove(zip_path)
    
# Temp Dict is set up like this 
#{"showurl": ["show", "episode"]}
# Conditions : Temp Exists and Temp is not empty
#              Temp does not exist
#              Temp is empty
def addtoTemp(url,show,episode):
    tfile = getLocalPath("temp.json")
    print( "\nTemp Waitlist Contains %s Episode %s" % (show,episode))
    if not os.path.exists(tfile):
        temp = {}
    elif(os.stat(tfile).st_size == 0):
        temp = {}
    else:
        with open(tfile, 'rb') as fp:
            temp = pickle.load(fp)
    temp[url] = [show,episode]
    with open(tfile, 'wb') as fp:
        pickle.dump(temp, fp)
    
# First Load the Temp File and Convert it to its propper format
def queueTemp():
    tfile = getLocalPath("temp.json")
    q = []
    if not os.path.exists(tfile):
        return []
    elif(os.stat(tfile).st_size == 0):
        return []
    else:
        with open(tfile, 'rb') as fp:
            temp = pickle.load(fp)
    # Assume we have a temp and queue this temp files using multiprocessing
    klist = list(temp.keys())
    for item in klist:
        show_out =  download_show(item,temp[item][0],temp[item][-1])
        if show_out:
            temp.pop(item)
            q.append(show_out)
    # Dump new temp list back minus successfully found shows
    with open(tfile, 'wb') as fp:
        pickle.dump(temp, fp)
    return q
        








def download_show(url,show, episode):
    link = ""
    dubbed = False
    retries = 6
    cwdir = getcwdir()
    s_path = os.path.join(cwdir,show)
    if not os.path.exists(s_path):
        os.makedirs(s_path)
    browser = get_browser()
    main_window = browser.current_window_handle
    while(retries>0):
        try:
            browser.refresh()
            time.sleep(random.randint(4, 8))
            link, dubbed = get_download_server(browser, url, main_window)
            if link:
                retries = 0
        except:
            if retries == 1 :
                addtoTemp(url,show,episode)
            retries = retries - 1
            close_any_alerts(browser)
            if DEBUG: print("Retrying %s with %s retries remaining" % (episode,retries))
    try:
        if not dubbed:
            download_subtitles(browser, show, episode, s_path)
    except:
        if DEBUG: print("No Subtitles Found Try Searching on https://subscene.com/")
    if link:
        return [s_path,link,"%s.mp4" % episode]
    else:
        return []



def selectBestQuality(test):
    test = [item for item in test if item is not None]
    qchart =  ["'h'","'n'","'l'"]
    for q in qchart:
        in_list = [q in x for x in test]
        if any(in_list):
            return test[in_list.index(1)]
    return ""
    





def get_download_server(browser, url, main_window):
    dubbed=False
    browser.get(url)
    #Change To Dub Server If it Exists
    if FIND_DUB_FIRST:
        try:
            time.sleep(2)
            dub_button = browser.find_element(By.XPATH, "//div[@class='item server-item'][@data-type='dub']")
            browser.execute_script("arguments[0].click();",dub_button)
            if DEBUG: print("Clicked Dub Button")
            dubbed=True
            
        except:
            if DEBUG: print("Failed To Click Dub Button")
    else:
        time.sleep(2)
    time.sleep(12)
    iframe_holder = browser.find_element('class name','anime_player')
    
    soup = BeautifulSoup(iframe_holder.get_attribute('innerHTML'),'html.parser')
    frames = [(frame.get('src')) for frame in soup.find_all('iframe')]
    frame = frames[-1]
    if DEBUG: print(frame)
    d_page = frame.split('?')[0].replace("embed-6","embed/a-download")
    browser.get(d_page)
    download_list = browser.find_elements('class name','dls-download')
    #download-list-ul
    #Check Possible Download Options for StreamSB
    for dlist in download_list:
        #print(dlist.get_attribute('innerHTML'),'html.parser')
        soup = BeautifulSoup(dlist.get_attribute('innerHTML'),'html.parser')
        download_ref = [(frame.get('href')) for frame in soup.find_all('a') if "streamsb" in frame.get('href')]
        if download_ref:
            browser.get(download_ref[0])
            #print("got Download")
            #print(soup.prettify())
        else:
            continue
    contentbox= browser.find_element('class name','col-lg-10')
    soup = BeautifulSoup(contentbox.get_attribute('innerHTML'),'html.parser')
    download_functions = [(frame.get('onclick')) for frame in soup.find_all('div')]
    high_quality_download = selectBestQuality(download_functions)
    browser.execute_script(high_quality_download)
    time.sleep(3)
    button = browser.find_element('class name','g-recaptcha')
    browser.execute_script("arguments[0].click();",button)
    time.sleep(3)
    # Passed the "Captcha" lol
    final_span_page = browser.find_element('class name','mb-4')
    soup = BeautifulSoup(final_span_page.get_attribute('innerHTML'),'html.parser')
    download_links = [(frame.get('href')) for frame in soup.find_all('a')]
    if DEBUG: print("Returned Download Link")
    return download_links[-1], dubbed


def getEpisodes(url,min_ep):
    browser = get_browser()
    main_window = browser.current_window_handle
    url = url
    browser.get(url)
    episodes = get_episodes_from_anime(browser)
    soup = BeautifulSoup(episodes.get_attribute('innerHTML'),'html.parser')
    lks = soup.find_all('a')
    links = [(anime_url_base + links.get('href')) for links in lks if int(links.getText()) > min_ep]
    episode_dict =  {episodes.text.splitlines()[i+min_ep]: links[i] for i in range(len(links))}
    return episode_dict
# Write Shows TO 
def output_shows(show_dict):
    with open(getLocalPath('episodes.txt'),'wb') as f:
        for key in show_dict.keys():
            output = str(key) + ":" + str(show_dict[key]) + "\n"
            f.write(output.encode("utf-8"))

def h_download(args):
    if args:
        args, lb_pos = args[0], args[1]
        return download_file(args[0],args[1],args[2],lb_pos)
    else:
        return ""

def main():
    #Iterate through the list of shows and download episodes that have not allready been downloaded
    #Load Show List And Progress
    q = queueTemp()
    process = current_process()
    # If you are not the main process, then you are a worker process and should not do anything
    #print(process.name)
    if not process.name == "MainProcess":
        #print(process.name)
        return []
    shows = get_shows()
    for show in shows.keys():
        print("Checking %s" % show)
        #Pass in the min show to download
        episodes = getEpisodes(anime_url_base+"/"+show, int(shows[show]))
        #If the show episode keys surpass the file episodes watched then download the new episodes
        e2d = list(episodes.keys())
        #queLinks means we need to download the episodes 
        qlinks = [episodes[ep] for ep in e2d]
        if qlinks:
            print("Downloading Episode(s) : " + str(" ".join(e2d)))
            #q = []
            for link in tqdm(qlinks, desc='Getting Episode Links'):
                try:
                    q.append((download_show(link,show,e2d.pop(0)),len(q)))
                except:
                    pass
                shows[show] = str(int(shows[show])+ 1)
        output_shows(shows)
    return q
# Concurrent Futures Creates Multiple Kids that run main() in parallel
if __name__ == "__main__":
    multiprocessing.freeze_support()
    q = main()
    browser = get_browser()
    browser.close()
    browser.quit()
    if q:
        print("Downloading %s Show(s) with Multiprocessing" % len(q))
        process_map(h_download, q)
