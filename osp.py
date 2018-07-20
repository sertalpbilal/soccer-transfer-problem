# -*- coding: utf-8 -*-


# Steps
# 1. Data
#    Get player stats
#    Get team list
#    Get team players
# 2. Model
#    Give budget as argument
#    Solve for maximizing team stats (total) under budget
# 3. Provide a list (team -> improvement -> budget)
# B. See which team actually improved their team most + see which team made the best improvement per dollar

import requests
import pandas as pd
from bs4 import BeautifulSoup

base = 'https://sofifa.com'

# Step 1. Data
def get_data():
    # Get all players as a list
    players = []
    url = '/players?offset=0'
    
    for page in range(50):
    
        print('Reading page ', page+1)
        response = requests.get(base + url)
        if response.status_code != 200:
            print('ERROR: ', response.status_code)
            return None
        soup = BeautifulSoup(response.content.decode('utf-8', 'ignore'), 'html.parser')
        players.extend(read_players_page(soup))
        pdf = pd.DataFrame(players, columns=['name', 'link', 'img', 'age', 'pos', 'value', 'overall', 'potential'])
        next_link = soup.find('a', string='Next')
        url = next_link.get('href')

    print(pdf.to_string())
    pdf.to_pickle('playerdb.pickle')
    

def read_players_page(soup):
    page = []
    divs = soup.find_all('div', {'class': 'col-name'})#,'a')
    for div in divs:
        links = div.find_all('a')
        for link in links:
            if link.get('title') is not None and '/player/' in link.get('href'):
                name = link.get('title')
                href = link.get('href')
                break
        else:
            continue
        poses = div.find_all('span', {'class': 'pos'})
        pos = ', '.join(p.string for p in poses)
        # Row stats
        row = div.parent.parent
        img = str(row.find('img', class_='player-check').get('data-src'))
        value = str(row.find('div', {'class': 'col-vl'}).string)
        age = str(row.select('div.col-ae')[0].string)
        ovr = str(row.select('div.col-oa > span')[0].string)
        pot = str(row.select('div.col-pt > span')[0].string)

        page.append([name, href, img, age, pos, value, ovr, pot])
    return page

# Optional: Read player data (calculated page)

if __name__ == '__main__':
    get_data()
