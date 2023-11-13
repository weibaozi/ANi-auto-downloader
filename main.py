import requests
from selenium import webdriver
from bs4 import BeautifulSoup
import urllib
import time
import os
import yaml
import opencc
import threading
import datetime
from tqdm import tqdm
import keyboard

def download(url,location=None):
    response = requests.get(url,stream=True)
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Get the file content
        file_content = response.content
        filename = os.path.basename(url)
        filename = urllib.parse.unquote(filename)
        save_path = filename
        if location is not None:   
            save_path = os.path.join(location, filename)
        # Save the file content to the specified path

        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)

        # total_size = int(response.headers.get('content-length', 0))
        # with open(save_path, 'wb') as file, tqdm(
        #     desc=filename,
        #     total=total_size,
        #     unit='B',
        #     unit_scale=True,
        #     unit_divisor=1024,
        # ) as bar:
        #     for data in response.iter_content(chunk_size=1024):
        #         file.write(data)
        #         bar.update(len(data))


        print(f"File downloaded and saved as {save_path}")
        return True
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")
        return False
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(options=options)
setting=yaml.load(open('setting.yaml',encoding='utf-8').read(), Loader=yaml.FullLoader)    
url = setting['url']
root_location = setting['location']
print(url,root_location)

def get_anime_data(filename):
    filename=filename[6:]
    name=filename.split(' - ')[-2]
    episode=filename.split(' - ')[-1]
    episode=episode.split(' [')[0]
    return name,episode

def CHS_to_CHT(string):
    s2t=opencc.OpenCC('s2t.json')
    return s2t.convert(string)

def download_helper(file_class,animes=None,anime=None):
    text=file_class.text
    parent_url=file_class.find_parent('a')['href']
    #clear redundant after .mp4
    if '.mp4' in parent_url:
        parent_url=parent_url.split('.mp4')[0]+'.mp4'
        download_url=urllib.parse.urljoin(url,parent_url)
        print("downloading",text)
        folder_name,episode=get_anime_data(text)
        save_location=os.path.join(root_location,folder_name)
        #create location if not exist
        if not os.path.exists(save_location):
            try:
                os.makedirs(save_location)
                #FileExistsError
            except:
                pass
        dw=download(download_url,save_location)
        # time.sleep(5)
        if anime is not None:
            if dw:
                animes[anime]=max(animes.get(anime,0),int(episode))
                yaml.dump(animes,open('animes.yaml','w',encoding='utf-8'),allow_unicode=True)
            
        return True
#run every 10 minutes
while True:
    print("start running at:", datetime.datetime.now())
        
    animes=yaml.load(open('animes.yaml',encoding='utf-8').read(), Loader=yaml.FullLoader)
    # Navigate to the webpage
    driver.get(url)
    # Wait for the page to load (you might need to adjust the wait time)
    driver.implicitly_wait(10)
    time.sleep(10)
    # Get the page source after it has fully loaded
    page_source = driver.page_source
    # Parse the page source with BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')
    #get the links of the animes
    links=soup.find_all('div',class_='mdui-row')
    if len(links)==0:
        print("No links found")
        # continue
    tmp=links[0]
    for link in links:
        if "[ANi]" in link.text:
            tmp=link
    links=tmp
    file_classes = links.find_all(class_='tool_tip')
    queue_files={}
    queue_anime_episode={}
    threads=[]

    for anime,epi in animes.items():
        for file_class in file_classes:
            text=file_class.text
            #print(anime,epi)
            anime_t=CHS_to_CHT(anime)
            name,episode=get_anime_data(text)
            episode=int(episode)
            if anime_t in name:
                
                if not epi+1<=episode:
                    break
                elif epi+1==episode:
                    #dw=download_helper(file_class)
                    thread=threading.Thread(target=download_helper,args=(file_class,animes,anime_t,))
                    threads.append(thread)
                    thread.start()

                else:
                    if anime_t not in queue_files:
                        queue_files[anime_t]=[]
                    queue_files[anime_t].append((episode,file_class))
                    print("queue",text)
                    # queue_anime_episode[anime]=max(queue_anime_episode.get(anime,0),episode)
    #sort
    queue_files={anime:sorted(file_classes,key=lambda x:x[0]) for anime,file_classes in queue_files.items()}
    #print(queue_files)
    for anime,file_classes in queue_files.items():
        for _,file_class in file_classes:
            thread=threading.Thread(target=download_helper,args=(file_class,animes,anime,))
            threads.append(thread)
            thread.start()
            # thread.join()

    threads=[thread.join() for thread in threads]
    # yaml.dump(animes,open('animes.yaml','w',encoding='utf-8'),allow_unicode=True)    
    for _ in tqdm(range(600),desc="sleeping 10 min:",bar_format="{desc}{percentage:3.0f}%|{bar}|{n_fmt}/{total_fmt}"):
        time.sleep(1)      
    # time.sleep(600)    
# print(file_classes[0].find_parent())