FROM python:3.11

RUN mkdir /app
WORKDIR /app

COPY . /app/
RUN pip install -r req.txt

#CMD [ "python", "./start_up.py"]
#CMD [ "python", "./telegram_updates_checking.py"]
#CMD [ "python", "./my_dispatcher.py"]
#CMD [ "python", "./file_generate.py"]
#CMD [ "python", "./bot_logic.py"]
#CMD [ "python", "./updates_consumer.py"]
