FROM python:latest

WORKDIR /usr/src/KiTraderBot

COPY . .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r dependencies.txt

ENTRYPOINT [ "python", "-u", "bot.py" ]