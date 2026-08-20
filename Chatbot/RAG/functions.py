from importlib_resources import read_text
from pypdf import PdfReader 
import re 


# reading data from pdf and put them in extracted file
def read_file(pdf_path ):
    data = PdfReader(pdf_path)
    extract_txt = ''
    for page in data.pages:
        extract_txt += page.extract_text()

    return extract_txt



# write extracted text into file 
def extracting(data , path):
    with open(path , 'w' , encoding='utf-8') as file:
        file.write(data)
    print("Done..")



#  read txt file (extracted)
def read(path):
    with open(path , 'r' , encoding='utf-8') as f:
        data = f.read()
    return data



# write data into file
def write(path , data):
    with open(path, 'w', encoding='utf-8') as f:
            f.write(data)



import re
import unicodedata

def cleaning(data, path, total_pages=131):
    text = unicodedata.normalize('NFKC', data)
    text = text.replace('\xad', '').replace('\u200b', '').replace('\xa0', ' ')

    # ---- remove the repeating title header line ----
    text = re.sub(
        r'Type\s*2\s*diabetes\s*in\s*adults\s*:\s*management\s*\(NG28\)\s*',
        ' ', text, flags=re.IGNORECASE
    )

    # ---- Remove the NICE copyright/footer block ----
    # Anchor on the URL fragment, which can itself be split across a line
    # wrap mid-word (e.g. "terms-and-\nconditions"). We match liberally
    # from up to ~120 chars BEFORE the URL fragment (to catch "© NICE
    # 2026. All rights reserved. Subject to Notice of rights (") through
    # the closing ")." after it — this doesn't depend on © decoding
    # correctly, exact wording spacing, or the phrase not being pre-split.
    text = re.sub(
        r'[^\n]{0,120}?'                      # up to 120 chars before URL (same line/paragraph only)
        r'nice\s*\.?\s*org\s*\.?\s*uk\s*/\s*'  # tolerate stray spaces from bad extraction
        r'te\s*r?\s*m\s*s\s*-?\s*a\s*n\s*d\s*-?\s*\n?\s*'
        r'con\s*di\s*ti\s*ons\s*#?\s*notice\s*-?\s*of\s*-?\s*rights\s*'
        r'\)?\.?\s*',
        ' ', text, flags=re.IGNORECASE | re.DOTALL
    )

    # fallback: simpler direct match in case the fuzzy one above is too strict
    text = re.sub(
        r'©?\s*NICE\s*\d{4}\.{0,2}\s*All\s*rights\s*reserved\.{0,2}\s*'
        r'Subject\s*to\s*Notice\s*of\s*rights\s*\(.*?\)\.{0,2}\s*',
        ' ', text, flags=re.IGNORECASE | re.DOTALL
    )

    # last-resort fallback: strip any leftover URL to this domain outright
    text = re.sub(r'https?://[^\s)]*nice\.org\.uk[^\s)]*', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'©', ' ', text)

    # ---- separate "Page N of 131" from text glued directly after it ----
    text = re.sub(
        rf'(Page\s*\d+\s*of\s*{total_pages})(?=\S)',
        r'\1\n',
        text, flags=re.IGNORECASE
    )

    # ---- remove any other stray URLs ----
    text = re.sub(r'https?://\S+', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'www\.\S+', ' ', text, flags=re.IGNORECASE)

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.match(r'^Contents\s*$', line, re.IGNORECASE):
            continue
        if re.search(r'\.{4,}\s*\d+\s*$', line):
            continue

        line = re.sub(r'[~`@#$%^&*_+=\[\]{}|\\<>؟]', ' ', line)
        line = line.replace('•', '-')

        line = re.sub(r'\s+', ' ', line).strip()
        line = re.sub(r'^\s*[\.\-]\s*$', '', line)

        if line:
            cleaned_lines.append(line)

    final_text = '\n'.join(cleaned_lines)
    final_text = re.sub(r'\n{2,}', '\n', final_text)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(final_text)

    print("Done..")
    return final_text