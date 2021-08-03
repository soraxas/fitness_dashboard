FROM python:3.7

WORKDIR /app

ADD . /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 8085

CMD ["python", "app.py"]
