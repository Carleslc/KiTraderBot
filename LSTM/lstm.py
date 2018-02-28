# LSTM for closing bitcoin price with regression framing
import os
import subprocess
import math
import numpy as np
import matplotlib.pyplot as plt
from pandas import read_csv
from keras.models import Sequential, load_model
from keras.layers import Dense
from keras.layers import LSTM
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

COINMARKETCAP = "../coinmarketcap-history/coinmarketcap_usd_history.py"

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

# convert an array of values into a dataset matrix
def create_dataset(dataset):
  dataX, dataY = [], []
  for i in range(len(dataset)-1):
    dataX.append(dataset[i])
    dataY.append(dataset[i + 1])
  return np.asarray(dataX), np.asarray(dataY)

# fix random seed for reproducibility
np.random.seed(36)

# load the dataset
#proc = subprocess.Popen(['python2', COINMARKETCAP, 'bitcoin','2013-04-28','2018-02-27'], stdout=subprocess.PIPE)
#with open('../LSTM/bitcoin.csv', 'wb') as csv:
#    csv.write(proc.stdout.read())
df = read_csv('bitcoin.csv')
df = df.drop(['Date','Open','High','Low','Volume','Market Cap', 'Average (High + Low / 2)'], axis=1)
df.info()
print(df.head())
df = df.iloc[::-1]
dataset = df.values
dataset = dataset.astype('float32')

# normalize the dataset
scaler = MinMaxScaler(feature_range=(0, 1))
dataset = scaler.fit_transform(dataset)

#prepare the X and Y label
X, y = create_dataset(dataset)

#Take 80% of data as the training sample and 20% as testing sample
trainX, testX, trainY, testY = train_test_split(X, y, test_size=0.20, shuffle=False)

# reshape input to be [samples, time steps, features]
trainX = np.reshape(trainX, (trainX.shape[0], 1, trainX.shape[1]))
testX = np.reshape(testX, (testX.shape[0], 1, testX.shape[1]))

# create and fit the LSTM network
#model = Sequential()
#model.add(LSTM(4, input_shape=(1, 1)))
#model.add(Dense(1))
#model.compile(loss='mean_squared_error', optimizer='adam')
#model.fit(trainX, trainY, epochs=5, batch_size=1, verbose=2)

#save model for later use
#model.save('savedModel')

#load_model
model = load_model('savedModel')

# make predictions
trainPredict = model.predict(trainX)
testPredict = model.predict(testX)

print("Test predict", testPredict[-1])
lastPrice = scaler.transform(df['Close'].iloc[-1])
futurePredict = model.predict(np.asarray([lastPrice]))
futurePredict = scaler.inverse_transform(futurePredict)

# invert predictions
trainPredict = scaler.inverse_transform(trainPredict)
trainY = scaler.inverse_transform(trainY)
testPredict = scaler.inverse_transform(testPredict)
testY = scaler.inverse_transform(testY)

print("Price for last 5 days: ")
print(testPredict[-5:])
print("Bitcoin price for tomorrow: ", futurePredict)

# calculate root mean squared error
trainScore = math.sqrt(mean_squared_error(trainY[:,0], trainPredict[:,0]))
print('Train Score: %.2f RMSE' % (trainScore))
testScore = math.sqrt(mean_squared_error(testY[:,0], testPredict[:,0]))
print('Test Score: %.2f RMSE' % (testScore))

# shift train predictions for plotting
trainPredictPlot = np.empty_like(dataset)
trainPredictPlot[:, :] = np.nan
trainPredictPlot[1:len(trainPredict)+1, :] = trainPredict

# shift test predictions for plotting
testPredictPlot = np.empty_like(dataset)
testPredictPlot[:, :] = np.nan
testPredictPlot[len(trainPredict):len(dataset)-1, :] = testPredict

# plot baseline and predictions
plt.plot(scaler.inverse_transform(dataset))
plt.plot(trainPredictPlot)
plt.plot(testPredictPlot)
plt.show()