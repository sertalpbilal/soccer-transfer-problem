
from PIL import Image, ImageDraw, ImageFont
import glob
import pandas as pd
import textwrap



# Constants

positions = {
    # Forward - 1
    'LS': (1,6),
    'ST1': (2,6),
    'ST': (3,6),
    'ST2': (4,6),
    'RS': (5,6),
    # Forward - 2
    'LW': (0,5),
    'LF': (1,5),
    'CF1': (2,5),
    'CF': (3,5),
    'CF2': (4,5),
    'RF': (5,5),
    'RW': (6,5),
    # Midfield - 1
    'LAM': (1,4),
    'CAM1': (2,4),
    'CAM': (3,4),
    'CAM2': (4,4),
    'RAM': (5,4),
    # Midfield - 2
    'LM': (0,3),
    'LCM': (1,3),
    'CM1': (2,3),
    'CM': (3,3),
    'CM2': (4,3),
    'RCM': (5,3),
    'RM': (6,3),
    # Midfield - 3
    'LWB': (0,2),
    'LDM': (1,2),
    'CDM1': (2,2),
    'CDM': (3,2),
    'CDM2': (4,2),
    'RDM': (5,2),
    'RWB': (6,2),
    # Defense
    'LB': (0,1),
    'LCB': (2,1),
    #'CB1': (2,1),
    'CB': (3,1),
    #'CB2': (4,1),
    'RCB': (4,1),
    'RB': (6,1),
    # Goalkeeper
    'GK': (3,0)
}

font = ImageFont.truetype("arial", 13)
font_title = ImageFont.truetype("arial", 15)
radius = 12

def convert_csv_to_plot():

    for team in glob.glob('squads/*.csv'):
        im_left = get_team_split_image(team, 'old')
        im_right = get_team_split_image(team, 'new')

        background = Image.new('RGBA', (930, 596), (255, 255, 255, 255))
        bg_w, bg_h = background.size
        background.paste(im_left, (0, 0))
        background.paste(im_right, (490, 0))

        team_name = team.split('\\')[1].split('.')[0]
        background.save('squads/{}.png'.format(team_name), 'PNG', quality=90)

    # PIL.Image.fromarray

def get_team_split_image(team, ttype):
    team_name = team.split('\\')[1].split('.')[0]
    print(team_name, ttype)

    squad = pd.read_csv(team)
    im = Image.open("soccer_field_small.jpg")
    width, height = im.size
    draw = ImageDraw.Draw(im)

    draw.rectangle([0, 0, width, 20], fill='white')
    team_rating = squad['Old.R'] if ttype == 'old' else squad['New.R']
    title_text = team_name + ' ({:.0f})'.format(team_rating.iloc[-1])
    w, h = font_title.getsize(title_text)
    draw.text((width / 2 - w / 2, 2), title_text, font=font_title, fill='gray')

    for index, row in squad.iterrows():
        if row['Pos'] in positions:
            x, y = positions[row['Pos']]
            centerx = width / 8.0 * (x + 1)
            centery = height / 8.0 * (6 - y + 1)
            draw_player(centerx, centery, radius, draw, row, ttype)

    return im

def draw_player(centerx, centery, radius, draw, row, ptype):

    if ptype == 'old' or row['Old'] == row['New']:
        circle_color = 'blue'
    else:
        circle_color = 'red'
    player_rating = str(round(row['Old.R'] if ptype == 'old' else row['New.R']))
    player_name = row['Old'] if ptype == 'old' else row['New']

    # Draw Circle
    draw.ellipse((centerx - radius, centery - radius,
                  centerx + radius, centery + radius), fill=circle_color,
                 outline=circle_color)

    # Draw Rating
    text = player_rating
    w, h = font.getsize(text)
    draw.text((centerx - w / 2, centery - h / 2), text, font=font, fill='white')

    # Draw Name
    multiline_text = textwrap.wrap(player_name, width=16)
    y_text = 0
    for line in multiline_text:
        w1, h1 = font.getsize(line)
        draw.text(
            (centerx - w1 / 2 + 1, centery - h1 / 2 + 21 + y_text),
            line, font=font, fill='gray')
        draw.text((centerx - w1 / 2, centery - h1 / 2 + 20 + y_text), line,
                  font=font, fill='black')
        y_text += h1 + 2

    # Draw Price
    if ptype == 'new' and row['Old'] != row['New']:
        price = '€{:.1f}'.format(row['Paid'] / 1e+6).replace('.0', '') + 'M'
        w2, h2 = font.getsize(price)
        draw.text((centerx - w2 / 2 + 1, centery - h2 / 2 - 20 + 1), price, fill='gray',
                  font=font)
        draw.text((centerx - w2/2, centery - h2/2 - 20), price, fill='red', font=font)


convert_csv_to_plot()