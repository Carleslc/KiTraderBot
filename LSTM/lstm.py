# LSTM for closing bitcoin price with regression framing
import os
import subprocess
import math
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from keras.models import Sequential, load_model
from keras.layers import Dense
from keras.layers import LSTM
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, accuracy_score
from sklearn.model_selection import train_test_split

COINMARKETCAP = "../coinmarketcap-history/coinmarketcap_usd_history.py"
DATE_FORMAT = "%Y-%m-%d"
LAST_DAYS = 7
DAYS_TO_PREDICT = 5
HISTORY = 365 * 3

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

todayDate = datetime.date.today()
today = todayDate.strftime(DATE_FORMAT)

# load model if trained today
newModel = True
if os.path.isfile('modelDate'):
    with open('modelDate', 'r') as date:
        if todayDate == datetime.datetime.strptime(date.read(), DATE_FORMAT).date():
            newModel = False
            print('Loading model...')
            model = load_model('savedModel')

# load the dataset
if newModel:
    print('Downloading bitcoin data...')
    proc = subprocess.Popen(['python2', COINMARKETCAP, 'bitcoin', '2013-04-28', today], stdout=subprocess.PIPE)
    with open('../LSTM/bitcoin.csv', 'wb') as csv:
        csv.write(proc.stdout.read())

df = pd.read_csv('bitcoin.csv')
df = df.drop(['Open','High','Low','Volume','Market Cap', 'Average (High + Low / 2)'], axis=1)

# insert last price at the beginning
lastPrice = float(input("Enter last BTCUSD price: "))
lastPriceRow = [{'Date': todayDate.strftime("%b %d %Y"), 'Close': lastPrice}]
df = pd.concat([pd.DataFrame(lastPriceRow), df], ignore_index=True)

print(df.shape)
print(df.head())
df = df.drop('Date', axis=1)
df = df.iloc[::-1]
dataset = df.values[-HISTORY:]
dataset = dataset.astype('float32')

# normalize the dataset
scaler = MinMaxScaler(feature_range=(0, 1))
dataset = scaler.fit_transform(dataset)

#prepare the X and Y label
X, y = create_dataset(dataset)

#Take 80% of data as the training sample and 20% as testing sample
trainX, testX, trainY, testY = train_test_split(X, y, test_size=0.2, shuffle=False)

# reshape input to be [samples, time steps, features]
trainX = np.reshape(trainX, (trainX.shape[0], 1, trainX.shape[1]))
testX = np.reshape(testX, (testX.shape[0], 1, testX.shape[1]))

if newModel:
    # create and fit the LSTM network
    model = Sequential()
    model.add(LSTM(4, input_shape=(1, 1)))
    model.add(Dense(1, use_bias=True))
    model.compile(loss='mean_squared_error', metrics=['accuracy'], optimizer='adam')
    model.fit(trainX, trainY, epochs=5, batch_size=1, verbose=2, validation_data=(testX, testY))

    #save model for later use
    print('Saving model...')
    model.save('savedModel')
    with open('modelDate', 'w') as date:
        date.write(today)

# make predictions
trainPredict = model.predict(trainX)
testPredict = model.predict(testX)

def predict(normalizedPrice):
    return scaler.inverse_transform(model.predict(np.array([normalizedPrice])))

mean_deviation = scaler.inverse_transform((np.array(testPredict[-LAST_DAYS:]) - np.array(testY[-LAST_DAYS:])).mean())
print("Mean deviation:", mean_deviation)

futurePredict = np.empty(DAYS_TO_PREDICT)
for i in range(len(futurePredict)):
    prediction = predict(scaler.transform(lastPrice)) - mean_deviation
    futurePredict[i] = prediction
    lastPrice = prediction
futurePredict = np.array([[p] for p in futurePredict]).reshape(-1, 1)

# calculate root mean squared error on historic data
trainScore = math.sqrt(mean_squared_error(trainY[:,0], trainPredict[:,0]))
print('Train Score: %.2f RMSE' % (trainScore))
testScore = math.sqrt(mean_squared_error(testY[:,0], testPredict[:,0]))
print('Test Score: %.2f RMSE' % (testScore))

# invert predictions
trainPredict = scaler.inverse_transform(trainPredict)
trainY = scaler.inverse_transform(trainY)
testPredict = scaler.inverse_transform(testPredict)
testPredict[-LAST_DAYS:] -= mean_deviation
testY = scaler.inverse_transform(testY)

print(f"Price for last {LAST_DAYS} days:")
print(testY[-LAST_DAYS:])
print(f"Predicted price for last {LAST_DAYS} days:")
print(testPredict[-LAST_DAYS:])
print(f"Predicted price for next {DAYS_TO_PREDICT} days:")
print(futurePredict)
tomorrow = (todayDate + datetime.timedelta(days=1)).strftime("%b %d %Y")
print(f"Predicted price for {tomorrow}: {futurePredict[0]}")

extension = np.concatenate((dataset, np.empty((DAYS_TO_PREDICT, 1))))
def prepareToPlot(predict, fromIndex, toIndex):
    predictPlot = np.empty_like(extension)
    predictPlot[:, :] = np.nan
    predictPlot[fromIndex:toIndex,:] = predict
    return predictPlot

# plot baseline and predictions
plt.plot(scaler.inverse_transform(dataset))
to1 = len(trainPredict)
to2 = to1 + len(testPredict)
to3 = to2 + len(futurePredict)
plt.plot(prepareToPlot(trainPredict, 0, to1))
plt.plot(prepareToPlot(testPredict, to1, to2))
plt.plot(prepareToPlot(futurePredict, to2, to3))
plt.show()