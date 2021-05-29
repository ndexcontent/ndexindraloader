# Use an official Python runtime as a parent image
FROM continuumio/miniconda3

RUN apt-get update
RUN apt-get install -y build-essential 

RUN mkdir /tmp/ndexindraloader
COPY ./ /tmp/ndexindraloader/
RUN pip install /tmp/ndexindraloader

RUN rm -rf /tmp/ndexindraloader

RUN mkdir /ndexindraloader
WORKDIR /ndexindraloader

CMD /bin/echo "To use run: ndexloadindra.py"
