from __future__ import print_function

import os
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import numpy as np
from keras.utils import np_utils

import re
import nltk

from bs4 import BeautifulSoup
from nltk.corpus import stopwords

from sklearn.externals import joblib
from sklearn.pipeline import Pipeline
import pickle
import h5py


from keras.preprocessing import sequence, text
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation
from keras.layers import Embedding
from keras.layers import Conv1D, GlobalMaxPooling1D

def news_to_wordlist(news_text, remove_stopwords=False):
	news_text = BeautifulSoup(news_text).get_text()
	news_text = re.sub("[^a-zA-Z]"," ", news_text)
	words = news_text.lower().split()
	if remove_stopwords:
		stops = set(stopwords.words("english"))
		words = [w for w in words if not w in stops]
	return(words)

def news_to_sentences( news_text, tokenizer, remove_stopwords=False ):
	raw_sentences = tokenizer.tokenize(news_text.decode('utf8').strip())
	sentences = []
	for raw_sentence in raw_sentences:
		if len(raw_sentence) > 0:
			sentences.append(news_to_wordlist( raw_sentence, \
			  remove_stopwords ))
	return sentences

if __name__ == '__main__':
	train = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'train.csv'))
	test = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'test.csv'))

	train = train.dropna(subset = ['text', 'type'])
	test = test.dropna(subset = ['text', 'type'])
	
	train = train.reset_index(drop=True)
	test = test.reset_index(drop=True)

	train_data_features = []
	test_data_features = []

	for i in range( 0, len(train["text"])):
		train_data_features.append(" ".join(news_to_wordlist(str(train["text"][i]), True)))
	
	for i in range( 0, len(test["text"])):
		test_data_features.append(" ".join(news_to_wordlist(str(test["text"][i]), True)))

	x_train = train_data_features
	x_test = test_data_features

	max_features = 5000
	maxlen = 400
	batch_size = 32
	embedding_dims = 50
	filters = 250
	kernel_size = 3
	hidden_dims = 250
	epochs = 2
	
	y_train = train["type"]
	y_train = y_train.iloc[:].values
	y_test = test["type"]
	y_test = y_test.iloc[:].values

	tk = text.Tokenizer(nb_words=2000, lower=True, split=" ")
	tk.fit_on_texts(np.concatenate([x_train]))
	joblib.dump(tk, 'models/tokenizer.pkl', compress=9)
	
	x_train = tk.texts_to_sequences(x_train)
	x_test = tk.texts_to_sequences(x_test)
	

	x_train = sequence.pad_sequences(x_train, maxlen=maxlen)
	x_test = sequence.pad_sequences(x_test, maxlen=maxlen)
	model = Sequential()

	model.add(Embedding(max_features,
	                    embedding_dims,
	                    input_length=maxlen))
	model.add(Dropout(0.2))

	model.add(Conv1D(filters,
	                 kernel_size,
	                 padding='valid',
	                 activation='relu',
	                 strides=1))
	model.add(GlobalMaxPooling1D())

	model.add(Dense(hidden_dims))
	model.add(Dropout(0.2))
	model.add(Activation('relu'))

	model.add(Dense(1))
	model.add(Activation('sigmoid'))

	model.compile(loss='binary_crossentropy',
	              optimizer='adam',
	              metrics=['accuracy'])
	
	model.fit(x_train, y_train,
	          batch_size=batch_size,
	          epochs=epochs,
	          validation_data=(x_test, y_test))

	loss_and_metrics = model.evaluate(x_test, y_test, batch_size=128)
	model.save("models/tensorflow.h5")
	print(loss_and_metrics)
