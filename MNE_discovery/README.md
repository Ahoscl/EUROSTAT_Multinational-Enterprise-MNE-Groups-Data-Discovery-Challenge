#  MNE Discovery

# Project Overview

**MNE_Discovery** is an automated Python-based system designed to identify and extract annual financial reports and other financial information of Multinational Enterprise (MNE) groups from public web sources. The system leverages Google's Programmable Search Engine (PSE), keyword-based relevance scoring, and custom logic to ensure accurate and efficient discovery of publicly available data.

## 1. Data Processing Steps

### 1.1. Custom Google Programmable Search Engine

Google's Programmable Search Engine (PSE) and API are used to perform efficient and scalable web searches. Two sets of queries are used:

- **Final Reports:** Targets annual reports specifically
- **Other Financial Data:** Gathers broader financial information

## 2. Methods and Models Used

## 2.1. Querying Process for Annual Reports (Final Reports)

For each company, a query is dynamically generated:
```
"{company_name} annual report {reference_year} filetype:pdf"
```
- **company_name:** From the input CSV file
- **reference_year:** Target year for the report
- **filetype:pdf:** Restricts results to PDF documents

The Google API returns:
- **Title**
- **Snippet**
- **Link**

These results are evaluated through a scoring system. The highest-scoring link is saved to the FIN_REP column in the output discovery.csv file.

### 2.2. Reference Year Extraction and Scoring

Years mentioned in the result snippets or titles are extracted. More recent years are scored higher.

### 2.3. Keyword-Based Scoring

Three keyword lists are applied:

- **Banned Terms:** Completely excluded if in title; penalized if in snippet
- **Good Terms:** Positive scores when found in any field (title, snippet, or link)
- **Super Terms:** Strong bonus if found across all three fields

### 2.4. Additional Scoring Criteria

Additional logic includes:

- **Ranking Score:** Higher API ranks receive better scores
- **Company Name Match:** Rewards for mentions in title, snippet, or link
- **Domain Match:** Rewards if the result is from the company’s official domain
- **Reference Year Match:** Bonus if reference year in top results matches the target or previous year and matches company domain
- **Extra Point:** If the link appeared among the top three search results, the company name matched the domain of the URL, and the reference year detected by the program matched the input reference year or was equal to (reference year - 1), an additional high score was assigned.

**The top result based on final score is selected as the Final Report.**

## 3. Process for Additional Financial Information (OTHERS)

### 3.1. Target Websites

Four financial information sources are used:

- `site:companiesmarketcap.com revenue`
- `site:finance.yahoo.com/quote/`
- `site:google.com/finance/quote/`
- `site:reuters.com/markets/companies/`

Each company is queried for each domain, retrieving a maximum of 10 results per site.

### 3.2. Evaluation and Selection Process

Selection follows these rules:

- **Step 1:** Rank 1 result with company name in title and snippet
- **Step 2:** Non-rank-1 result with company name in both title and snippet
- **Step 3:** Title match only
- **Step 4:** If none, select the first available result

One link per company per site is selected and written to discovery.csv.


## 4. Runtime and Performance

The system was tested on ~200 companies with a runtime of approximately 45 minutes. This is considered efficient given the dependence on real-time Google search results. The code supports parallel execution and uses performance-optimized logic.

## 5. Code Modularity and Reusability

Modular design with separate files for querying (make_discovery_csv.py), scoring (score_tools.py), and I/O (io_tools.py)

- Configurable keyword lists and target sites
- Fully documented and reusable components
- Easily extendable for new data sources or formats

## 6. Setup & Usage

### 6.1. Requirements

Python 3.8+  
Required packages listed in `requirements.txt`

### 6.2. Execution

python MNE_Discovery.py  
-- **input:** data/discovery.csv  
-- **output:** ../discovery.csv

### 6.3. Example CSV Format

ID;NAME;TYPE;SRC;REFYEAR  
18490453;ADECCO GROUP AG;FIN_REP;https://www.adeccogroup.com/.../the-...-report-2023.pdf;2023  
18490453;ADECCO GROUP AG;OTHER;https://companiesmarketcap.com/inr/adecco-group/revenue/;2024  
18490453;ADECCO GROUP AG;OTHER;https://finance.yahoo.com/quote/AHEXY/;2024  
18490453;ADECCO GROUP AG;OTHER;https://www.reuters.com/markets/companies/ADEN.S/;2024  
18490453;ADECCO GROUP AG;OTHER;https://www.google.com/finance/quote/SGSN:SWX;2024  
18490453;ADECCO GROUP AG;OTHER;;  
...
## 7. License

This project is for academic and research purposes only.