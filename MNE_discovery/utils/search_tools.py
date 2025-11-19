import requests
import os
from dotenv import load_dotenv
import pandas as pd
import urllib.parse
import time

load_dotenv()

API_FINREPORTS = os.getenv('api_key_finreports')
CX_FINREPORTS = os.getenv('cse_finreports')


# Search for PDF reports on a specific website.
def search_fin_reports(query):
    results = []
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={API_FINREPORTS}&cx={CX_FINREPORTS}&num=10&start=1"
    print(url)
    response = requests.get(url, verify=False)
    data = response.json()

    if 'items' in data:
        for item in data['items']:
            results.append({
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
            })

    print(results)
    return results


def search_other_fins(company_list, refyear):
    others_data = []
    for idx, row in company_list.iterrows():
        company = row['NAME']
        ID = row['ID']

        others_webs = [
            'site:companiesmarketcap.com revenue',
            'site:finance.yahoo.com/quote/',
            'site:google.com/finance/quote/',
            'site:reuters.com/markets/companies/'
        ]

        for webpage in others_webs:
            raw_query = f'{company.lower()} {webpage}'
            encoded_query = urllib.parse.quote(raw_query)

            # It is assumed that a service like Google Custom Search is being used.
            results = search_fin_reports(encoded_query) or []

            seen_links = set()
            for i, r in enumerate(results):
                link = r.get('link')
                if link in seen_links or not link:
                    continue
                seen_links.add(link)

                others_data.append({
                    'ID': ID,
                    'NAME': company,
                    'TITLE': r.get('title'),
                    'LINK': link,
                    'SNIPPET': r.get('snippet'),
                    'ORDER': i + 1,
                    'search term': webpage
                })

            time.sleep(1)

    df = pd.DataFrame(others_data)

    # Remove duplicate rows.
    df.drop_duplicates(subset=['NAME', 'LINK'], inplace=True)

    # Add the 'REFYEAR' column.
    df['REFYEAR'] = refyear
    return df
