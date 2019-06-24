# -*- coding: utf-8 -*-

import requests
import pandas as pd
from bs4 import BeautifulSoup
import multiprocessing

base = 'https://sofifa.com'

def get_url(page_url):
    print('Requesting page ', page_url)
    response = requests.get(base + page_url)
    if response.status_code != 200:
        print('ERROR: ', response.status_code)
        return None
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup

def fix_currency(amount):
    amount = amount[1:]
    fldigits = 0
    if '.' in amount:
        fldigits = len(amount.split('.')[1])-1
    amount = amount.replace('.', '')
    if 'M' in amount:
        amount = amount.replace('M', '')
        amount = amount + '0'*(6-fldigits)
    elif 'K' in amount:
        amount = amount.replace('K', '')
        amount = amount + '0'*(3-fldigits)
    return int(amount)

def get_player_list(page_url):
    soup = get_url(page_url)
    return read_players_page(soup)

# Step 1. Data
def get_player_db(pages=200):
    # Get all players as a list
    players = []
    url = '/players?col=oa&sort=desc&offset={}'
    
    url_list = [url.format(60*i) for i in range(pages)]
    
    pool = multiprocessing.Pool(processes=20)
    pool_outputs = pool.map(get_player_list, url_list)
    for r in pool_outputs:
        players.extend(r)
    pool.close()
    pool.join()
    
    pdf = pd.DataFrame(players, columns=['name', 'link', 'img', 'age', 'pos', 'value', 'overall', 'potential'])
    pdf.to_pickle('playerdb.pickle')
    pdf.to_csv('playerdb.csv', encoding='utf-8-sig')
    
    return pdf
    

def read_players_page(soup):
    page = []
    table = soup.find('table').find_all('tr')
    for row in table:
        links = row.find_all('a')
        for link in links:
            if link.get('title') is not None and '/player/' in link.get('href'):
                name = link.get('title')
                href = link.get('href').rsplit('/', 2)[0]
                break
        else:
            continue
        poses = row.find('td', {'class': 'col-name'}).find_all('span', {'class': 'pos'})
        pos = ', '.join(p.string for p in poses)
        # Row stats
        img = str(row.find('img').get('data-src'))
        value = str(row.find('td', {'class': 'col-vl'}).string)
        value = fix_currency(value)
        age = int(row.select('td.col-ae')[0].string)
        ovr = int(row.select('td.col-oa > span')[0].string)
        pot = int(row.select('td.col-pt > span')[0].string)

        page.append([name, href, img, age, pos, value, ovr, pot])
    return page

def get_player_info(player):

    if player != '':

        soup = get_url(player)
        pinfo = {'link': player}
        # Name
        t = soup.find('div', {'class': 'meta'}).find('a').previousSibling
        pinfo['name'] = t.string.split('(')[0].rstrip()
        t = soup.find('div', {'class': 'card-body stats'})
        overall = int(t.find('span', {'class': 'label'}).text)
        pinfo['overall'] = overall
        return pinfo
    else:
        pinfo = {'link': '', 'name': '', 'overall': 0, 'potential': 0}
        return pinfo

def get_team_info(team):
    
    if type(team) == str:
        url = '/teams?keyword=' + team.replace(' ', '%20')
        soup = get_url(url)
        links = soup.find_all('a')
        for link in links:
            if '/team/' in link.get('href'):
                team_url = link.get('href')
                break

        # At this point we should have team id
        url = str(team_url)
        soup = get_url(url)

        budget = str(soup.find('label', string='Transfer Budget').next.next).replace('\t', '')
        budget = fix_currency(budget)

        startings = soup.find_all('tr', class_='starting')
        player_list = []
        position_list = []
        ratings = []
        team_info = {}

        for row in startings:
            for i in row.find_all('a'):
                if '/player/' in i.get('href'):
                    clean_url = i.get('href').rsplit('/', 2)[0]
                    player_list.append(clean_url)
                    break
            position = row.find_all('td')[5].find('span').string
            position_list.append(position)
            ratings.append(int(row.find('td', class_='col-oa').find('span').string))


        team_info['players'] = player_list
        team_info['positions'] = position_list
        team_info['ratings'] = ratings
        team_info['budget'] = budget
    elif team is None:
        team_info = {'players': ['']*11,
                     'positions': ['GK', 'LB', 'LCB', 'RCB', 'RB',
                                    'LCM', 'CM', 'RCM', 'CAM',
                                    'LS', 'RS'],
                     'ratings': [0]*11,
                     'budget': 0
                     }


    return team_info


if __name__ == '__main__':
    get_player_db()
