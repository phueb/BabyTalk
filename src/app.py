from flask import Flask, request
# import numpy as np
from flask import jsonify


app = Flask(__name__)
app.config.from_pyfile('server_configs.py')


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@app.route('/', methods=['POST'])
def generate():

    text = request.form.get('text')

    res = {'result': text + ' COMPLETION'}

    return jsonify(res)


# def generate_terms(model,
#                    terms,
#                    num_samples=50,
#                    num_phrases=2,
#                    num_words=4,
#                    sort_column=None,
#                    special_symbols=('OOV'),
#                    exclude_special_symbols=False):
#     bptt_steps = model.configs_dict['bptt_steps']
#     output_list = []
#     if exclude_special_symbols:
#         excluded_term_ids = [model.hub.train_terms.term_id_dict[symbol] for symbol in special_symbols]
#     else:
#         excluded_term_ids = []
#     for i in range(num_phrases):
#         num_terms_in_phrase = len(terms)
#         term_ids = [model.hub.train_terms.term_id_dict[term] for term in terms]
#         while not len(term_ids) == num_words + len(terms):
#
#             # get softmax probs
#             x = np.asarray(term_ids)[:, np.newaxis][-bptt_steps:].T
#             feed_dict = {model.graph.x: x}
#             softmax_probs = np.squeeze(model.sess.run(model.graph.softmax_probs, feed_dict=feed_dict))
#
#             # calc new term_id and add
#             samples = np.zeros([model.hub.train_terms.num_types], np.int)
#             total_samples = 0
#             while total_samples < num_samples:
#                 softmax_probs[0] -= sum(softmax_probs[:]) - 1.0  # need to compensate for float arithmetic
#                 new_sample = np.random.multinomial(1, softmax_probs)
#                 term_id_ = np.argmax(new_sample)
#                 if term_id_ not in excluded_term_ids:
#                     samples += new_sample
#                     total_samples += 1
#             term_id = np.argmax(samples)
#             term_ids.append(term_id)
#
#         # convert phrase to string and add to output_list
#         phrase_str = ' '.join([model.hub.train_terms.types[term_id] for term_id in term_ids[num_terms_in_phrase:]])
#         output_list.append(phrase_str)
#
#     # sort
#     if sort_column is not None:
#         output_list.sort(key=lambda x: x[sort_column])
#     return output_list


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
