from bs4 import BeautifulSoup
from urllib.request import urlopen
import requests
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from datetime import datetime, timedelta
from lxml import html
from apscheduler.schedulers.blocking import BlockingScheduler
import time

cred = credentials.Certificate("./myloc-1571525204357-firebase-adminsdk-x55mt-fcf4afe1b3.json")
firebase_admin.initialize_app(cred, {'databaseURL':'https://myloc-1571525204357.firebaseio.com/'})

cookies = { 'afisha.sid':'s%3AqVKZb4OPJbvtQoIV9ccvZ0UnRO9i8ZTg.Es7iWs0rP2cIgTA3HtNVH8Lkwgau80w%2BDBK6QsaCZ7U',
               '_csrf': 'OeFTDT_63OhBsFubnyT68S3H'         
         }
user_agent  = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 YaBrowser/19.9.3.314 Yowser/2.5 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru,en-us;q=0.7,en;q=0.3',
        'Accept-Encoding': 'deflate',
        'Accept-Charset': 'windows-1251,utf-8;q=0.7,*;q=0.7',
        'Keep-Alive': '300',
        'Connection': 'keep-alive' 
        }
results = []
data = []

def get_html(url):  
     r = requests.get(url, headers=user_agent,  cookies= cookies).text  
     return r


def find_elements_on_page(r):    
    all_film = BeautifulSoup(r, 'lxml')
    links = all_film.find('main', class_='main rubric-type-events')
    link_films = links.find_all('div', class_='events-list__item')
    return link_films

def newfilm_info(nf, data):
    info_film = BeautifulSoup(nf, 'lxml')    
    name = info_film.find('div', class_='event-concert-description__title-info').text
    img = info_film.find('img', class_='image event-concert-heading__poster').get('src')
    d_text = info_film.find('div', class_='concert-description__text-wrap').text
    g = info_film.find('ul', class_='tags tags_size_l tags_theme_light event-concert-heading__tags')
    gsAll= g.findAll('li')
    genre = ''
    for gs in gsAll:
        genre += gs.text + ' '

    
    inf = info_film.findAll('div', class_='event-attributes__row')    
    for pi in inf:
        if (pi.find('dt', class_='event-attributes__category').text == 'Премьера'):
            pr = pi.find('dd', class_='event-attributes__category-value').text
        if (pi.find('dt', class_='event-attributes__category').text == 'Режиссёр'):
            director = pi.find('a', class_='event-person__name').text
        if (pi.find('dt', class_='event-attributes__category').text == 'Время'):
            duration = pi.find('dd', class_='event-attributes__category-value').text
        if (pi.find('dt', class_='event-attributes__category').text == 'Страна'):
            country = pi.find('dd', class_='event-attributes__category-value').text

    results.append({
        'img': img,
        'name': name,
        'country': country,
        'director': director, 
        'genre': genre,
        'pr': pr,
        'text': d_text,
        'duration': duration,
        'sessions': data 
        })        
    return(results)

def wrap_element(link):
    p = requests.get(link, headers=user_agent, cookies=cookies).text 
    new_page = BeautifulSoup(p, 'lxml')
    seance = new_page.findAll('div', class_='Wrapper-vciaga-1 dvmLjH')
    return seance

def get_page_data(films):    
    static = 'https://afisha.yandex.ru/'
    t = 0
    for film in films:
        post = db.reference('films')
        g = static + film.find('a').get('href')
        input_info(g, post)        
        time.sleep(120)

def input_info(g, post):
    nf = requests.get(g, headers=user_agent, cookies=cookies).text
    post.set(newfilm_info(nf, date_ses(g)))  


        
def date_ses(g):

    url_seance = g.replace('preset=today', 'date=')
    
    today = datetime.now()
    delta = timedelta(days=1)
    future = today - delta

    while True:    
        
        future = future + delta 
        link = url_seance + str(future.strftime("%Y-%m-%d"))
        time.sleep(60)        
        p = requests.get(link, headers=user_agent, cookies=cookies).text 
        new_page = BeautifulSoup(p, 'lxml')
        sc = new_page.findAll('div', class_='Wrapper-vciaga-1 dvmLjH')        

        if sc:            
            for s in sc:
                name_c = s.find('a', class_='afisha-common-venue-name').text
                adres = s.find('div', class_='afisha-common-venue-address').text
                times = s.find_all('a', class_='afisha-common-session-list_button')
                time_t =''
                for ti in times:
                    time_t += ti.text + ' '
        

                data.append({ 
                    'cinema': name_c,
                    'adress': adres,
                    'date': str(future.strftime("%Y-%m-%d")),
                    'time': time_t
                    })         
                
            future = future + delta
        else:
            break 

        return data

def main():
    while True:
        page = 1
        url = 'https://afisha.yandex.ru/saint-petersburg/selections/cinema-today?page={}'.format(str(page))   
        
        element = find_elements_on_page(get_html(url))
        if element:
            get_page_data(element)
            page = page + 1
        else:
            break 
           

def scheduled_job():
  main()


sched = BlockingScheduler()
@sched.scheduled_job('cron', day_of_week='mon-fri', hour=7)
sched.start()

