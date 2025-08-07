import requests
from bs4 import BeautifulSoup
import re

url = 'https://fantasy.premierleague.com/api/bootstrap-static/'

url2 = 'https://fantasy.premierleague.com/api/element-summary/442/'



data = requests.get(url2).json()
print(data)

# Print player name + ID
# for player in data['elements']:
#     print(f"{player['first_name']} {player['second_name']} - ID: {player['id']}")

