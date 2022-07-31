import json
import requests
import numpy as np
from time import sleep
from random import randint
from bs4 import BeautifulSoup


url = 'https://pureportal.coventry.ac.uk/en/organisations/school-of-economics-finance-and-accounting/publications/?page ='
pages = np.arange(1, 14, 1)

publications = []
for page in pages:
    _url = url + str(page)
    web_page = requests.get(_url)
    sleep(randint(5, 15))
    soup = BeautifulSoup(web_page.content, "html.parser")
    documents = soup.findAll("div", {"class" : "rendering rendering_researchoutput rendering_researchoutput_portal-short rendering_contributiontojournal rendering_portal-short rendering_contributiontojournal_portal-short"})


    for doc in documents:
        title = doc.find("h3", {"class" : "title"})
        pub_link = title.find('a', {'class':'link'}).get('href')
        pub_title = title.find('span').text
        try:
            author = doc.find('a', {'class':'link person'})
            author_link = author.get('href')
            author_name = author.find('span').text
        except Exception as e:
            continue

        publication = {
            'title':{
                'pub_title':pub_title,
                'pub_link':pub_link
            },
            'author':{
                'author_name':author_name,
                'author_link':author_link
            }
        }
        publications.append(publication)

def save_data(article_dict):
    with open('publications.txt', 'w') as output_file:
        json.dump(article_dict, output_file)

save_data(publications)