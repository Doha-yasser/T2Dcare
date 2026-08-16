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



#  cleaning data
def cleaning(data, path):
    lines = data.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if re.search(r'https?://|www\.', line):
            cleaned_lines.append(line)
            continue
        
        if re.search(r'Page\s*\d+', line):
            cleaned_lines.append(line)
            continue
        
       
        line = re.sub(r'[~{}()،:؛]', ' ', line)
        # flags=re.IGNORECASE ---> ignore case sensitivity
        line = re.sub(r'©\s*NICE\s*\d{4}\.?', '', line, flags=re.IGNORECASE)
        line = re.sub(r'\s+', ' ', line)
        line = line.strip()
        
        if line:  # only add non-empty lines
            cleaned_lines.append(line)
    with open(path ,'w' , encoding='utf-8') as f:
        f.write('\n'.join(cleaned_lines))
    print('added')