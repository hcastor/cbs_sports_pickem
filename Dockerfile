FROM python:3

WORKDIR /flsk
COPY requirements.txt /
RUN pip install -r /requirements.txt

COPY secrets.py .
COPY flsk.py .

ENTRYPOINT ["python"]
CMD ["flsk.py"]
