# https://www.tensorflow.org/beta/tutorials/text/text_generation


from __future__ import absolute_import, division, print_function, unicode_literals

import tensorflow as tf
import numpy as np
import os
import iteratortools as it
import programtokenizer
import model_maker
import json
import sys


# CONSTANTS #


ERROR_LOG_FILE = os.path.join(it.ERROR_LOG_PATH, 'modelload.csv')

BATCH_SIZE = 64
BUFFER_SIZE = 10000
CHECKPOINT_DIR = os.path.join('.', 'training_checkpoints')
WORD_TO_INDEX_FILE = 'word_to_index.json'

EPOCHS = 10


# FUNCTIONS #


def split_input_target(chunk):
    input_text = chunk[:-1]
    target_text = chunk[1:]
    return input_text, target_text


def loss(labels, logits):
    return tf.keras.losses.sparse_categorical_crossentropy(labels, logits, from_logits=True)


def write_index(index, vocab_size, variable_char_start):
    if not os.path.exists(CHECKPOINT_DIR):
        os.makedirs(CHECKPOINT_DIR)
    with open(os.path.join(CHECKPOINT_DIR, WORD_TO_INDEX_FILE), 'w') as fp:
        json.dump({'index_to_token': index, 'vocab_size': vocab_size, 'variable_char_start': variable_char_start}, fp)


def tokenize_c(programs):
    tokenized = []
    print("Tokenizing C programs:")
    progress_bar = it.ProgressBar(0, len(programs))
    progress_bar.print_progress_bar()
    for program in programs:
        try:
            tokenized.append(programtokenizer.tokenize_c(program))
            progress_bar.increment_work()
        except Exception:
            progress_bar.increment_errors()
        finally:
            progress_bar.print_progress_bar()
    return "".join(tokenized)

def tokenize_python(programs):
    tokenized = []
    print("Tokenizing Python Programs:")

    progress_bar = it.ProgressBar(0, len(programs))
    progress_bar.print_progress_bar()
    for program in programs:
        try:
            tokenized.append(programtokenizer.tokenize_python(program))
            progress_bar.increment_work()
        except KeyError:
            progress_bar.increment_errors()
        finally:
            progress_bar.print_progress_bar()
    return "".join(tokenized)


def tokenize_lang(programs, lang):
    if lang.lower() == "c":
        text = tokenize_c(programs)
    elif lang.lower() == "python":
        text = tokenize_python(programs)
    else:
        print("Sorry, we don't have a tokenizer in place for {}".format(lang))
        sys.exit(1)
    return text


# MAIN METHOD #


if __name__ == '__main__':
    print('Scanning contents of files into memory')
    lang = sys.argv[1]
    if sys.argv[2] == '-l':
        load_from_file = True
    else:
        load_from_file = False
    # if lang.lower() in 'python':
    #     file_paths = it.get_file_paths()
    #     text = get_as_file(file_paths)
    # else:
    if load_from_file:
        with open(os.path.join(it.REPO_ROOT_PATH, "data", "{}_tokenized.txt".format(lang)), encoding='utf8') as f:
            text = f.read()
    else:
        programs = it.get_lang_files(lang)
        if len(programs) is 0:
            print('No files found with {} as a language'.format(lang))
            sys.exit(1)
        text = tokenize_lang(programs, lang)
        with open("c_tokenized.txt", "w", encoding='utf8') as f:
            f.write(text)

    print('Length of text: {} characters'.format(len(text)))
    vocab = sorted(set(text))
    print('{} unique tokens'.format(len(vocab)))

    token_to_index = {t: i for i, t in enumerate(vocab)}
    index_to_token = np.array(vocab)
    write_index(token_to_index, len(vocab), programtokenizer.get_var_char_index())
    text_as_int = np.array([token_to_index[t] for t in text])

    seq_length = 100
    examples_per_epoch = len(text)//seq_length

    # Create training examples/targets
    char_dataset = tf.data.Dataset.from_tensor_slices(text_as_int)
    sequences = char_dataset.batch(seq_length + 1, drop_remainder=True)

    dataset = sequences.map(split_input_target)
    dataset = dataset.shuffle(BUFFER_SIZE).batch(BATCH_SIZE, drop_remainder=True)

    # Model:
    vocab_size = len(vocab)
    model = model_maker.build_model(
        vocab_size=len(vocab),
        embedding_dim=model_maker.EMBEDDING_DIMENSION,
        rnn_units=model_maker.RNN_UNITS,
        batch_size=BATCH_SIZE
    )

    for input_example_batch, target_example_batch in dataset.take(1):
        example_batch_predictions = model(input_example_batch)
        sampled_indices = tf.random.categorical(example_batch_predictions[0], num_samples=1)
        sampled_indices = tf.squeeze(sampled_indices, axis=-1).numpy()

        example_batch_loss = loss(target_example_batch, example_batch_predictions)
        print("Prediction shape: ", example_batch_predictions.shape, " # (batch_size, sequence_length, vocab_size)")
        print("scalar_loss:      ", example_batch_loss.numpy().mean())

    model.compile(optimizer='adam', loss=loss)

    # Checkpoints:
    checkpoint_prefix = os.path.join(CHECKPOINT_DIR, "ckpt_{epoch}")
    checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=checkpoint_prefix,
        save_weights_only=True
    )

    history = model.fit(dataset, epochs=EPOCHS, callbacks=[checkpoint_callback])
