# Latest stable version of Python 3
FROM python:3-alpine

WORKDIR /usr/src/KiTraderBot

COPY . .

# Needed for some dependencies (not available in alpine by default)
RUN apk --no-cache add gcc musl-dev

# Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r dependencies.txt

ENTRYPOINT [ "python", "-u", "bot.py" ]