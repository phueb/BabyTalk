from flask import Flask, request, make_response
from flask import jsonify
from pathlib import Path
from functools import reduce
from operator import iconcat
import pandas as pd


app = Flask(__name__)

CORPUS_NAME = 'childes-20191206'
MAX_CHARACTERS = 8


# load tokens
p = Path(__file__).parent.parent / 'corpora' / f'{CORPUS_NAME}.txt'
if not p.exists():  # on pythonanywhere.com
    p = Path(__file__).parent / 'corpora' / f'{CORPUS_NAME}.txt'
text_in_file = p.read_text()
docs = text_in_file.split('\n')
tokens = reduce(iconcat, [d.split() for d in docs], [])  # flatten list of lists
vocab = set(tokens)

N_GRAM_SIZE = 3

# collect n-grams and their next words
ngram2next_words = {}
for i in range(len(tokens) - N_GRAM_SIZE):
    for size in range(1, N_GRAM_SIZE + 1):
        seq = tuple(tokens[i:i + size])
        if seq not in ngram2next_words:
            ngram2next_words[seq] = []
        ngram2next_words[seq].append(tokens[i + N_GRAM_SIZE])


def with_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@app.route('/babytalk-demo', methods=['POST', 'GET'])
def babytalk_demo():

    text = request.form.get('text')

    if text is None:
        return with_headers(make_response("No text submitted", 400))

    words = tuple(['.'] + text.split())

    # check vocab
    for w in words:
        if w not in vocab:
            return with_headers(make_response(f'"{w}" not in vocab', 400))

    while True:

        words = words[1:]
        if not words:
            return with_headers(make_response(f'Did not find {N_GRAM_SIZE}-gram in corpus', 400))

        try:
            next_words = ngram2next_words[words]
        except KeyError:
            print('Not in n-grams')
            continue

        # make html table
        col2data = {n: [] for n in range(len(words) + 1)}
        for nw in next_words:
            for n, w in enumerate(list(words) + [nw]):
                col2data[n].append(w)
        df = pd.DataFrame(data=col2data)
        table_html = df.to_html(index=False, header=False).replace('border="1"', 'border="0"')

        return with_headers(make_response(jsonify({'result': table_html})))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
