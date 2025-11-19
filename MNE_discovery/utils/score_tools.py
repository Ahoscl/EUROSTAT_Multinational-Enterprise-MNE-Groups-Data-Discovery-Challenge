import re
from urllib.parse import urlparse
import pandas as pd


def score_terms (df, terms):
    # query order points
    mapping = {1: 10, 2: 8, 3: 5, 4: 3, 5: 2, 6: 1}
    df ['ORDER_POINT'] = df ['ORDER'].apply(lambda x: mapping.get(x, 0))

    # term points (title, link, snippet)
    for field in ['TITLE', 'LINK', 'SNIPPET']:
        df [f"{field}_POINT"] = df [field].apply(
            lambda text: sum(1 for term in terms if isinstance(text, str) and term.lower() in text.lower())
        )

    # Company name matching score
    df ['COMPANY_MATCH_POINT'] = df.apply(lambda row: sum(
        1 for field in ['TITLE', 'LINK', 'SNIPPET']
        if str(row ['NAME']).lower() in str(row [field]).lower()
    ), axis = 1)

    # Domain matching score (whether it appears within the website link).

    def extract_domain_root (domain_full):
        domain_full = domain_full.lower().replace("www.", "")
        parts = domain_full.split('.')

        # If the domain has a three-part structure such as .co.jp, .com.tr, or .ac.uk, extract the first segment.
        if len(parts) >= 3 and parts [-2] in {'co', 'com', 'ac'}:
            return parts [-3]
        elif len(parts) >= 2:
            return parts [-2]
        else:
            return parts [0]

    def name_match (row):
        company = str(row.get('NAME', '')).lower()
        link = str(row.get('LINK', '')).lower()

        # Clean the company name.
        company = re.sub(r'\b(inc|plc|s\.a\.?|corp|corporation|co|limited|ltd|company|aktiebolag|ag|a/s|sa|nv|ab)\b',
                         '', company)
        company = re.sub(r'[^a-z0-9 ]+', '', company)
        company_words = [w for w in company.split() if len(w) >= 2]

        if not company_words:
            return 0

        parsed_link = urlparse(link)
        domain_full = parsed_link.netloc.replace("www.", "").lower()
        domain_root = extract_domain_root(domain_full)

        first_word = company_words [0]

        # For multi-word names, utilize combinations or initials.
        if len(company_words) >= 2:
            combo = ''.join(company_words [:2])
            if combo == domain_root or combo in domain_root:
                return 10
            initials = ''.join([w [0] for w in company_words])
            if initials == domain_root:
                return 10

        # Single-word or general check
        if first_word == domain_root or first_word in domain_root:
            return 10

        return 0

    # apply func
    df ['DOMAIN_MATCH_POINT'] = df.apply(name_match, axis = 1)

    # total point and order
    df ['TOTAL_TERM_POINT'] = df [
        ['TITLE_POINT', 'LINK_POINT', 'SNIPPET_POINT', 'COMPANY_MATCH_POINT', 'DOMAIN_MATCH_POINT']].sum(axis = 1)
    df ['TOTAL_POINT'] = df ['TOTAL_TERM_POINT'] + df ['ORDER_POINT']

    df = df.sort_values(by = ['NAME', 'TOTAL_POINT'], ascending = [True, False])
    return df


def score_super_point (df, terms, refyear):
    df ['TITLE_SUPER_POINT'] = 0
    df ['SNIPPET_SUPER_POINT'] = 0
    df ['LAST_SUPER_POINT'] = 0

    for idx, row in df.iterrows():
        name = row ['NAME']
        title = str(row.get('TITLE', ''))
        snippet = str(row.get('SNIPPET', ''))
        fname = re.split(r"[ /&\-+]", name) [0].lower()

        order = row ['ORDER']
        domain_match = row.get('DOMAIN_MATCH_POINT', 0)
        order_point = row.get('ORDER_POINT', 0)
        refyear_point = row.get('REFYEARPOINT', 0)

        fname_match_title = re.search(rf"\b{re.escape(fname)}\b", title.lower())
        fname_match_snippet = re.search(rf"\b{re.escape(fname)}\b", snippet.lower())

        refyear_assigned = False

        # TITLE
        for term in terms:
            if fname_match_title and term.lower() in title.lower():
                if str(refyear) in term:
                    df.at [idx, 'TITLE_SUPER_POINT'] = 10
                    df.at [idx, 'REFYEAR'] = str(refyear)
                    refyear_assigned = True
                    break
                elif str(refyear-1) in term and not refyear_assigned:
                    df.at [idx, 'TITLE_SUPER_POINT'] = 8
                    df.at [idx, 'REFYEAR'] = str(refyear - 1)
                    refyear_assigned = True
                    break

        # SNIPPET
        for term in terms:
            if fname_match_snippet and term.lower() in snippet.lower():
                if str(refyear) in term:
                    df.at [idx, 'SNIPPET_SUPER_POINT'] = 10
                    if not refyear_assigned:
                        df.at [idx, 'REFYEAR'] = str(refyear)
                        refyear_assigned = True
                    break
                elif str(refyear-1) in term and not refyear_assigned:
                    df.at [idx, 'SNIPPET_SUPER_POINT'] = 8
                    df.at [idx, 'REFYEAR'] = str(refyear - 1)
                    refyear_assigned = True
                    break

        # FINAL
        ref_year = df.at [idx, 'REFYEAR']
        if order in [1, 2, 3] and domain_match == 10 and ref_year in [str(refyear), str(refyear-1)]:
            df.at [idx, 'LAST_SUPER_POINT'] = (order_point * 3) + 5 * 2 + (refyear_point * 2)

    return df


def score_bad_points (df, terms):
    # Reset the TITLE_BAD_POINT column to zero at the beginning.
    df ['TITLE_BAD_POINT'] = 0

    for idx, row in df.iterrows():
        TITLE = row.get('TITLE', '')
        SNIPPET = row.get('SNIPPET', '')

        # For each term, perform a search within the TITLE or SNIPPET.
        for term in terms:
            if term.lower() in str(TITLE).lower() or term.lower() in str(SNIPPET).lower():
                df.at [idx, 'TITLE_BAD_POINT'] -= 20  # If the term is found, subtract points.

    return df


def refyear_and_score (df, refyear):
    df ['REFYEARPOINT'] = 0

    def extract_full_years (text):
        if not isinstance(text, str):
            return []
        return re.findall(r'\b(20\d{2})\b', text)

    def extract_fy_years (text):
        if not isinstance(text, str):
            return []
        matches = re.findall(r'FY\s?-?\(?20?(\d{2})\)?', text, re.IGNORECASE)
        full_years = []
        for y in matches:
            if len(y) == 2:
                if int(y) >= 50:
                    full_years.append('19' + y)
                else:
                    full_years.append('20' + y)
            else:
                full_years.append(y)
        return full_years

    df_without_year = df [df ['REFYEAR'].isna()]

    for idx, row in df_without_year.iterrows():
        title = row.get('TITLE', '')
        snippet = row.get('SNIPPET', '')
        link = row.get('LINK', '')

        year_found = None

        # 1. TITLE → full year
        title_years = extract_full_years(title)
        if title_years:
            year_found = title_years [0]

        # 2. TITLE → FY year
        if not year_found:
            fy_years = extract_fy_years(title)
            if fy_years:
                year_found = fy_years [0]

        # 3. SNIPPET → full year
        if not year_found:
            snippet_years = extract_full_years(snippet)
            if len(snippet_years) >= 2:
                year_found = snippet_years [1]
            elif snippet_years:
                year_found = snippet_years [0]

        # 4. SNIPPET → FY year
        if not year_found:
            fy_snippet = extract_fy_years(snippet)
            if fy_snippet:
                year_found = fy_snippet [0]

        # 5. LINK → full year
        if not year_found:
            link_years = extract_full_years(link)
            if link_years:
                year_found = link_years [-1]

        # 6. LINK → FY year
        if not year_found:
            fy_link = extract_fy_years(link)
            if fy_link:
                year_found = fy_link [0]

        if year_found:
            df.at [idx, 'REFYEAR'] = year_found

    # At this stage, assign scores to all REFYEAR entries.
    for idx, row in df.iterrows():
        year_found = str(row ['REFYEAR']) if pd.notna(row ['REFYEAR']) else ''
        if year_found == str(refyear):
            df.at [idx, 'REFYEARPOINT'] = 6
        elif year_found == str(refyear - 1):
            df.at [idx, 'REFYEARPOINT'] = 4
        elif year_found.isdigit() and refyear - 5 <= int(year_found) <= refyear - 2:
            df.at [idx, 'REFYEARPOINT'] = 2
        else:
            df.at [idx, 'REFYEARPOINT'] = 0

    return df
