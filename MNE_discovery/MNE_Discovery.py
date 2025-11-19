import pandas as pd
import time
import warnings
import urllib.parse
import unicodedata
import re
from utils.search_tools import search_fin_reports, search_other_fins
from utils.io_tools import save_to_excel
from utils.score_tools import score_terms, score_super_point, score_bad_points, refyear_and_score
from utils.make_discovery_csv import finrep_discovery_csv

warnings.filterwarnings('ignore')


class MNEFinancialReports:
    ref_year = 2024

    # Entries containing prohibited terms will either be excluded from the list or penalized with negative scores at a later stage.
    BANNED_TERMS = ['semi annual', 'semi-annual', 'semiannual', 'half annual', 'half-annual', 'half year', 'half-year',
                    'half‑yearly', 'interim', 'q3', 'q2', 'q1', '1q', '2q', '3q', 'first quarter', 'first-quarter',
                    'second quarter', 'second-quarter', 'third quarter', 'third-quarter', 'semi-year', 'semi year',
                    'semiyear', 'three-month', 'three month', 'six-month', 'six month', 'nine month', 'nine-month',
                    'h1', 'h2']

    # In the basic scoring, points will be assigned based on the presence of specific words
    GOOD_TERMS = ['annual', 'report', 'financial', 'statements', 'consolidated', str(ref_year),
                  str(ref_year - 1), 'integrated', 'sustainable', 'sustainability', 'review']

    # Additional points will be awarded to entries containing any of the following phrase patterns.
    SUPER_TERMS = ['annual report ' + str(ref_year), 'report ' + str(ref_year) + ' annual',
                   str(ref_year) + ' annual report', 'annual report ' + str(ref_year - 1),
                   'report ' + str(ref_year - 1) + ' annual', str(ref_year - 1) + ' annual report',
                   'sustainability report ' + str(ref_year - 1), 'sustainability report ' + str(ref_year)]

    def __init__ (self, input_csv='data/discovery.csv'):
        self.company_list = None
        self.all_data = []
        self.input_csv = input_csv

        self.excel_path = "output/FR_links.xlsx"
        self.scored_excel_path = "output/FR_links_w_points.xlsx"

        self.path_others = r'output/Others_all.xlsx'
        self.csv_others = r'output/Others_for_csv.xlsx'

        self.df = None
        self.df_others = None

        self.discovery_path = r"../discovery.csv"

    def load_company_list (self):
        df = pd.read_csv(self.input_csv, delimiter = ';')
        self.company_list = df [['ID', 'NAME']].drop_duplicates()

    def search_final_reports (self):
        referance_year = self.ref_year
        print("🔍 Searching for FIN_REP's...")
        for idx, row in self.company_list.iterrows():
            company = row ['NAME']
            ID = row ['ID']
            print(f"[{idx + 1}] {company}...")

            raw_query = f"{company} annual report " + str(referance_year) + " filetype:pdf"
            encoded_query = urllib.parse.quote(raw_query)

            results = search_fin_reports(encoded_query)

            seen_links = set()
            for i, r in enumerate(results):
                if r ['link'] in seen_links:
                    continue
                seen_links.add(r ['link'])

                self.all_data.append({
                    'ID': ID,
                    'NAME': company,
                    'TITLE': r ['title'],
                    'LINK': r ['link'],
                    'SNIPPET': r ['snippet'],
                    'ORDER': i + 1
                })

            time.sleep(1)

        self.df = pd.DataFrame(self.all_data)
        self._filter_unwanted_terms()

        self.df = self.df.drop_duplicates(subset = ['NAME', 'LINK'])

        self.df ['REFYEAR'] = None

        save_to_excel(self.df, self.excel_path)

    def _filter_unwanted_terms (self):
        pattern = '|'.join(term.lower() for term in self.BANNED_TERMS)
        self.df = self.df [~self.df ['TITLE'].str.lower().str.contains(pattern, na = False)]

    def score_links (self):
        if self.df is None:
            self.df = pd.read_excel(self.excel_path)

        # First, we identify the reference year and then assign scores; this step must function correctly before proceeding.
        self.df = refyear_and_score(self.df, self.ref_year)

        # We assign scores to individual words.
        self.df = score_terms(self.df, self.GOOD_TERMS)

        # We assign a premium score when keywords appear as a group
        self.df = score_super_point(self.df, self.SUPER_TERMS, self.ref_year)

        # Initially, we extract the title. If the snippet contains undesirable terms, we apply penalty scores.
        self.df = score_bad_points(self.df, self.BANNED_TERMS)

        self.df ['last_total'] = (
                self.df ['TOTAL_POINT'] +
                self.df ['TITLE_SUPER_POINT'] +
                self.df ['SNIPPET_SUPER_POINT'] +
                self.df ['TITLE_BAD_POINT'] +
                self.df ['REFYEARPOINT'] +
                self.df ['LAST_SUPER_POINT']
        )

        self.df = self.df.sort_values(by = ['ID', 'last_total'], ascending = [True, False])
        self.df.to_excel(self.scored_excel_path, index = False)
        print(f"✅ Skorlanmış dosya kaydedildi: {self.scored_excel_path}")

    def others_search (self):
        self.df_others = search_other_fins(self.company_list, self.ref_year)
        save_to_excel(self.df_others, path = self.path_others)

    def customize_others (self):
        # Text normalization
        def normalize_text (text):
            text = str(text).lower()
            text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
            text = re.sub(r'[^a-z0-9 ]+', ' ', text)  # Remove special characters.
            text = re.sub(r'\s+', ' ', text).strip()  # Eliminate unnecessary spaces.
            return text

        # Clean the company name (excluding titles)
        def clean_company_name (name):
            name = normalize_text(name)
            suffixes = r'\b(inc|plc|sa|corp|corporation|co|limited|ltd|company|aktiebolag|ag|a ' \
                       r's|nv|ab|group|aktiebolaget|p\.l\.c\.)\b'
            name = re.sub(suffixes, '', name)
            return re.sub(r'\s+', ' ', name).strip()

        # Verify the name-snippet correspondence for each record.
        def title_snippet_match (row):
            company = clean_company_name(row.get('NAME', ''))
            title = normalize_text(row.get('TITLE', ''))
            snippet = normalize_text(row.get('SNIPPET', ''))

            if not company:
                return pd.Series({'name_match': 0, 'snippet_match': 0})

            name_in_title = int(company in title)
            name_in_snippet = int(company in snippet)

            return pd.Series({'name_match': name_in_title, 'snippet_match': name_in_snippet})

        df = pd.read_excel(self.path_others)
        df [['name_match', 'snippet_match']] = df.apply(title_snippet_match, axis = 1)
        df.to_excel('output/others_for_control.xlsx', index = False)

        df_csv = pd.DataFrame()

        # Helper function
        def is_not_included (df_check, df_result):
            return ~df_check.set_index(['ID', 'search term']).index.isin(
                df_result.set_index(['ID', 'search term']).index)

        # Step 1: Records where ORDER = 1, name_match = 1, and snippet_match = 1.
        step1 = df [(df ['ORDER'] == 1) & (df ['name_match'] == 1) & (df ['snippet_match'] == 1)].copy()
        step1 ['source_step'] = 1
        df_csv = pd.concat([df_csv, step1], ignore_index = True)

        # Step 2: Records where ORDER ≠ 1, but name_match = 1 and snippet_match = 1.
        step2 = df [(df ['ORDER'] != 1) & (df ['name_match'] == 1) & (df ['snippet_match'] == 1)].copy()
        step2 = step2 [is_not_included(step2, df_csv)]
        step2 = step2.sort_values('ORDER').groupby(['ID', 'search term'], as_index = False).first()
        step2 ['source_step'] = 2
        df_csv = pd.concat([df_csv, step2], ignore_index = True)

        # Step 3: Records where name_match = 1, regardless of snippet_match status.
        step3 = df [df ['name_match'] == 1].copy()
        step3 = step3 [is_not_included(step3, df_csv)]
        step3 = step3.sort_values('ORDER').groupby(['ID', 'search term'], as_index = False).first()
        step3 ['source_step'] = 3
        df_csv = pd.concat([df_csv, step3], ignore_index = True)

        # Step 4: For entries not covered in the above steps, select the first one according to ORDER.
        step4 = df.copy()
        step4 = step4 [is_not_included(step4, df_csv)]
        step4 = step4.sort_values('ORDER').groupby(['ID', 'search term'], as_index = False).first()
        step4 ['source_step'] = 4
        df_remaining = step4.copy()
        df_csv = pd.concat([df_csv, step4], ignore_index = True)

        # Not Found and Remaining records
        df_not_ok = df [~df ['ID'].isin(df_csv ['ID'])] [['ID', 'NAME']].drop_duplicates()
        df_not_ok.to_excel('output/others_not_found.xlsx', index = False)
        df_remaining.to_excel('output/others_remaining.xlsx', index = False)

        # Final output
        df_csv.to_excel(self.csv_others, index = False)

    def final_discovery_csv (self):
        # 1. FIN_REP data
        self.df = pd.read_excel(self.scored_excel_path).groupby('NAME').head(1)

        # 2. original discovery.csv
        base_df = pd.read_csv(self.input_csv, sep = ';')

        # 3. OTHERS data
        df_others = pd.read_excel(self.csv_others)

        # 4. make output discovery.csv
        finrep_discovery_csv(base_df, self.df, df_others, self.discovery_path)


if __name__ == "__main__":
    finder = MNEFinancialReports()
    finder.load_company_list()
    finder.search_final_reports()
    finder.score_links()
    finder.others_search()
    finder.customize_others()
    finder.final_discovery_csv()
