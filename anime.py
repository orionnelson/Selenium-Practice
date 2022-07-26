import os
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as Firefox_Options
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import requests
from tqdm import tqdm
import zipfile

fb_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
geo_path = "E:\\Selenium-Practice\\Selenium-Practice\\geckodriver.exe"
serv = Service(geo_path)
firefox_options = Firefox_Options()
firefox_options.binary = fb_path
#driver = webdriver.Firefox(service=serv,options=firefox_options)
anime_url_base="https://4anime.gg"

# returns the current shows in episodes.txt as a dict split by showurl:episode
def get_shows():
    with open('episodes.txt','r+') as f:
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

#browser = get_browser()
#url = "https://4anime.gg/the-dawn-of-the-witch-17983/"

#browser.get(url)
#main_window = browser.current_window_handle

def get_episodes_from_anime(browser):
        # Counld not find a good
        episodes = browser.find_element('id','episodes-content')
        return episodes

def download_file(path,url,local_filename):
    CHNK_SZ = 8192 * 10
    local_filename = local_filename
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(os.path.join((path),(local_filename)), 'wb') as f:
            tt = r.headers['Content-length']
            with tqdm(total=int(tt), desc="Downloading "+ str(local_filename) )as pbar:
                    for chunk in r.iter_content(chunk_size=CHNK_SZ): 
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        #if chunk:
                        f.write(chunk)
                        pbar.update(int(CHNK_SZ))
    return local_filename

def download_subtitles(browser, show, episode, s_path):
    baseurl =  "https://www.opensubtitles.org"
    show = show.rsplit('-',1)[0]
    url = "https://www.opensubtitles.org/en/search2?MovieName=%s&action=search&SubLanguageID=eng&Episode=%s" % (show, episode)
    print("Downloading Subtitles for %s Episode %s" % (show, episode))
    browser.get(url) # bt-dwl-bt
    time.sleep(3)
    dload = browser.find_element('id','bt-dwl-bt')
    link = dload.get_attribute('href')
    r = requests.get(link, stream=True)
    zip_path = os.path.join(s_path,"%s.zip" % episode)
    with open(zip_path, 'wb' ) as fd:
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)
    print("Extracting Zip File Subtitles")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        ep_path  = "%s/%s" % (s_path,episode)
        os.mkdir(ep_path)
        zip_ref.extractall(ep_path)
    os.remove(zip_path)
    






def download_show(url,show, episode):
    cwdir = os.path.dirname(__file__)
    s_path = os.path.join(cwdir,show)
    if not os.path.exists(s_path):
        os.makedirs(s_path)
    browser = get_browser()
    main_window = browser.current_window_handle
    link = get_download_server(browser, url, main_window)
    #print(link)
    download_file(s_path,link,str(episode)+".mp4")
    #downloadthe Subtitles for the Show default English
    try:
        download_subtitles(browser, show, episode, s_path)
    except:
        print("No Subtitles Found Try Searching on https://subscene.com/")
        pass
    #url = "https://www.opensubtitles.org/en/search2?MovieName=black-summoner&action=search&SubLanguageID=eng&Episode=2"




    





def get_download_server(browser, url, main_window):
    browser.get(url)
    time.sleep(2)
    player_servers = browser.find_element('class name','player-servers')
    iframe_holder = browser.find_element('class name','anime_player')
    #print(player_servers.get_attribute('innerHTML'))
    #print(iframe_holder.get_attribute('innerHTML'))
    soup = BeautifulSoup(iframe_holder.get_attribute('innerHTML'),'html.parser')
    frames = [(frame.get('src')) for frame in soup.find_all('iframe')]
    frame = frames[-1]
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
        else:
            continue
    contentbox= browser.find_element('class name','contentbox')
    #print(contentbox.get_attribute('innerHTML'),'html.parser')
    soup = BeautifulSoup(contentbox.get_attribute('innerHTML'),'html.parser')
    download_functions = [(frame.get('onclick')) for frame in soup.find_all('a')]
    high_quality_download = [item for item in download_functions if "'h'" in item][-1]
    print("Retrieved High Quality Download Link")
    #print(high_quality_download)
    browser.execute_script(high_quality_download)
    time.sleep(3)
    button = browser.find_element('class name','g-recaptcha')
    browser.execute_script("arguments[0].click();",button)
    print("Beat Broken Captcha")
    time.sleep(3)
    # ASSUME WE BEAT THE CAPCHA WITHOUT USING OPENCV
    final_span_page = browser.find_element('class name','contentbox')
    soup = BeautifulSoup(final_span_page.get_attribute('innerHTML'),'html.parser')
    download_link = [(frame.get('href')) for frame in soup.find_all('a')][-1]
    print("Returned Download Link")
    return download_link


    #print(frames)


    #return download_server


def getEpisodes(url):
    browser = get_browser()
    main_window = browser.current_window_handle
    url = url
    browser.get(url)
    episodes = get_episodes_from_anime(browser)
    #print(episodes)
    #print(episodes.text)
    soup = BeautifulSoup(episodes.get_attribute('innerHTML'),'html.parser')
    links = [(anime_url_base + links.get('href')) for links in soup.find_all('a')]
    episode_dict =  {episodes.text.splitlines()[i]: links[i] for i in range(len(links))}
    #print(episode_dict)
    return episode_dict
# Write Shows TO 
def output_shows(show_dict):
    with open('episodes.txt','wb') as f:
        for key in show_dict.keys():
            output = str(key) + ":" + str(show_dict[key]) + "\n"
            #print(output.strip())
            f.write(output.encode("utf-8"))



def main():
    #Iterate through the list of shows and download episodes that have not allready been downloaded
    #Load Show List And Progress
    shows = get_shows()
    for show in shows.keys():
        print("Checking %s" % show)
        #print(shows[show])
        episodes = getEpisodes(anime_url_base+"/"+show)
        #print(episodes)
        #If the show episode keys surpass the file episodes watched then download the new episodes
        e2d = [ep for ep in episodes.keys() if int(ep) > int(shows[show])]
        #queLinks means we need to download the episodes 
        qlinks = [episodes[ep] for ep in e2d]
        if qlinks:
            print("Downloading Episodes:" + str(" ".join(e2d)))
            for link in qlinks:
                #print(shows[show])
                #print(type(shows[show]))
                download_show(link,show,e2d.pop(0))
                shows[show] = str(int(shows[show])+ 1)
                #print(shows[show])
        output_shows(shows)
    
main()
