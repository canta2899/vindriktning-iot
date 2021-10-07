FROM alpine

# Installing python
RUN apk add --update --no-cache python3
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

# Adding files
COPY ./mqtt_app/requirements.txt /
RUN pip3 install -r /requirements.txt
RUN	mkdir app 
ADD ./mqtt_app/run.sh .
RUN chmod o+x /run.sh
CMD ["sh", "run.sh"]
