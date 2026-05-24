import re

def clean_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Join hyphenated line breaks
    text = re.sub(r'-\s+([a-záàâãéêíóôõúüça-z])', r'\1', text)

    # Remove image descriptions
    text = re.sub(r'(Ao centro da imagem|Fim da audiodescrição|Figura \d+\.)[^\n]*\n', '', text)

    # Remove references block
    text = re.sub(r'DEITEL.*', '', text, flags=re.DOTALL)

    # Remove very short isolated lines (index garbage)
    lines = text.split('\n')
    lines = [l for l in lines if len(l.strip()) > 3 or l.strip() == '']
    text = '\n'.join(lines)

    # Collapse excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

import glob
import os

BASE = os.path.join(os.path.dirname(__file__), "documents")

for file in glob.glob(os.path.join(BASE, "**/*.txt"), recursive=True):
    if not file.endswith('.kate-swp'):
        clean_txt(file)
        print(f"Cleaned: {file}")
