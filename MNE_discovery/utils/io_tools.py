import re


def clean_excel_text (text):
    if isinstance(text, str):
        return re.sub(r"[\x00-\x1F]", "", text)
    return text


def save_to_excel (df, path):
    df = df.map(clean_excel_text)
    df.to_excel(path, index = False)
