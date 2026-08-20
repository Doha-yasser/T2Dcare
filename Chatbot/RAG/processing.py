import json
import re
import os
from functions import read 
import nltk


#---------------------  chunking as words -------------------------
def chunk_by_words(text, chunk_size=600, overlap=120):
    words = text.split()
    total_words = len(words)

    page_markers = []
    for match in re.finditer(r'Page\s*(\d+)\s*of\s*\d+', text, re.IGNORECASE):
        char_pos = match.start()
        word_pos = len(text[:char_pos].split())
        page_markers.append((word_pos, int(match.group(1))))

    chunks = []
    start = 0
    step = chunk_size - overlap

    while start < total_words:
        end = min(start + chunk_size, total_words)
        chunk_words = words[start:end]
        chunk_text = ' '.join(chunk_words)

        page_num = None
        for pos, pnum in reversed(page_markers):
            if pos <= start:
                page_num = pnum
                break

        chunks.append({
            "chunk_id": len(chunks) + 1,
            "text": chunk_text,
            "metadata": {
                "page": page_num,
                "word_count": len(chunk_words),
                "start_word": start,
                "end_word": end,
                "total_words": total_words,
                "chunk_size": chunk_size,
                "overlap": overlap
            }
        })
        start += step

    print(f"Created {len(chunks)} chunks")
    return chunks


# 2. Save function 

def save_chunks(chunks, json_path, txt_path):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("CHUNKS WITH METADATA\n")
        f.write(f"Total chunks: {len(chunks)}\n")
        f.write("=" * 70 + "\n\n")
        
        for c in chunks:
            meta = c["metadata"]
            f.write(f"{'─' * 70}\n")
            f.write(f" CHUNK #{c['chunk_id']}\n")
            f.write(f"{'─' * 70}\n")
            f.write(f"  Page: {meta['page']}\n")
            f.write(f"  Word count: {meta['word_count']}\n")
            f.write(f"  Start word: {meta['start_word']}\n")
            f.write(f"  End word: {meta['end_word']}\n")
            f.write(f"  Total words: {meta['total_words']}\n")
            f.write(f"  Chunk size: {meta['chunk_size']}\n")
            f.write(f"  Overlap: {meta['overlap']}\n")
            f.write(f"{'─' * 70}\n")
            f.write(f"\n{c['text']}\n")
            f.write(f"\n{'─' * 70}\n\n")
    
    print(f" TXT saved to: {txt_path}")




# ---------------- sentence chunking ----------------
import re
import json
from nltk.tokenize import sent_tokenize
from openai import OpenAI


client = OpenAI(api_key=os.getenv('API_KEY'))
def get_sentences(text):
    return sent_tokenize(text)


def chunk_by_sentences(text, sentences_per_chunk=2, overlap_sentences=1):
    sentences = get_sentences(text)
    total_sentences = len(sentences)
    print(f"Total sentences: {total_sentences}")

    page_markers = []
    for match in re.finditer(r'Page\s*(\d+)\s*of\s*\d+', text, re.IGNORECASE):
        char_pos = match.start()
        char_count = 0
        sentence_index = 0
        for i, sent in enumerate(sentences):
            if char_pos >= char_count and char_pos < char_count + len(sent):
                sentence_index = i
                break
            char_count += len(sent) + 1
        page_markers.append((sentence_index, int(match.group(1))))
    print(f"Found {len(page_markers)} page markers")

    chunks = []
    start = 0
    step = sentences_per_chunk - overlap_sentences

    while start < total_sentences:
        end = min(start + sentences_per_chunk, total_sentences)
        chunk_sentences = sentences[start:end]
        chunk_text = ' '.join(chunk_sentences)

        page_num = None
        for sent_idx, pnum in reversed(page_markers):
            if sent_idx <= start:
                page_num = pnum
                break

        chunks.append({
            "chunk_id": len(chunks) + 1,
            "text": chunk_text,
            "metadata": {
                "page": page_num,
                "sentence_count": len(chunk_sentences),
                "start_sentence": start,
                "end_sentence": end,
                "total_sentences": total_sentences,
                "sentences_per_chunk": sentences_per_chunk,
                "overlap_sentences": overlap_sentences
            }
        })
        start += step

    print(f"Created {len(chunks)} chunks")
    if chunks:
        avg = sum(c["metadata"]["sentence_count"] for c in chunks) / len(chunks)
        print(f"Average chunk size: {avg:.1f} sentences")
    return chunks


# ---------------- LLM enrichment: main points + question per chunk ----------------

def generate_chunk_summary(chunk_text, model="gpt-3.5-turbo", max_retries=3):
    prompt = f"""Given the following text chunk, respond ONLY with a JSON object (no markdown, no preamble) with exactly these keys:
- "main_points": an array of 1-3 short bullet points summarizing the key information in this chunk
- "question": a single natural-language question that this chunk answers

Text chunk:
\"\"\"
{chunk_text}
\"\"\"

Respond with only the JSON object."""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )

            raw = response.content[0].text.strip()
            raw = re.sub(r'^```json|```$', '', raw, flags=re.MULTILINE).strip()
            parsed = json.loads(raw)
            return {
                "main_points": parsed.get("main_points", []),
                "question": parsed.get("question", "")
            }
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")

    return {"main_points": [], "question": ""}


def enrich_chunks_with_summary(chunks, model="gpt-3.5-turbo"):
    for c in chunks:
        print(f"Summarizing chunk #{c['chunk_id']}...")
        summary = generate_chunk_summary(c["text"], model=model)
        c["metadata"]["main_points"] = summary["main_points"]
        c["metadata"]["question"] = summary["question"]
    return chunks


# ---------------- save chunks ----------------

def save_chunks(chunks, json_path, txt_path):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("SENTENCE CHUNKS WITH METADATA\n")
        f.write(f"Total chunks: {len(chunks)}\n")
        f.write("=" * 70 + "\n\n")

        for c in chunks:
            meta = c["metadata"]
            f.write(f"{'─' * 70}\n")
            f.write(f"CHUNK #{c['chunk_id']}\n")
            f.write(f"{'─' * 70}\n")
            f.write(f"  Page: {meta['page']}\n")
            f.write(f"  Sentence count: {meta['sentence_count']}\n")
            f.write(f"  Start sentence: {meta['start_sentence']}\n")
            f.write(f"  End sentence: {meta['end_sentence']}\n")
            f.write(f"  Total sentences: {meta['total_sentences']}\n")
            f.write(f"  Sentences per chunk: {meta['sentences_per_chunk']}\n")
            f.write(f"  Overlap: {meta['overlap_sentences']}\n")
            if meta.get("question"):
                f.write(f"  Question this chunk answers: {meta['question']}\n")
            if meta.get("main_points"):
                f.write(f"  Main points:\n")
                for point in meta["main_points"]:
                    f.write(f"    - {point}\n")
            f.write(f"{'─' * 70}\n")
            f.write(f"\n{c['text']}\n")
            f.write(f"\n{'─' * 70}\n\n")

    print(f"JSON saved to: {json_path}")
    print(f"TXT saved to: {txt_path}")