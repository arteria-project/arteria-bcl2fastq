Arteria bcl2fastq
=================

NOTE: This software is still in a pre-release state. Anything can and will happen!
With that said, improvement suggestions and PRs are very welcome if you want to try it out.

A self contained (Tornado) REST service for running Illuminas bcl2fastq.

Trying it out
-------------
    
    # install dependencies
    pip install -r requirements.txt .
    

Try running it:

     bcl2fastq-ws --config config/ --port 8888

And then you can find a simple api documentation by going to:

    http://localhost:8888/api/1.0


Running integration tests in docker container (with a centos base). First you need to change the
 `FROM arteria/frozendata:latest` to `FROM centos:6` as the base image for this container in not 
 yet public (but we hope to make it so in the future).

    docker build -t bcl2fastq-ws .
    docker run -v $PWD:/bcl2fastq-ws -p 8888:8888 -t -i bcl2fastq-ws:latest /bin/bash

    # Once inside the docker container execute
    cd /bcl2fastq-ws/ && pip install -r requirements.txt && python2.7 setup.py install && bcl2fastq-ws --config config/ --port 8888

Now you should have a image with Illuminas `bcl2fastq` installed as well as the `bcl2fastq-ws`, 
and it should be reachable on `localhost:8888`
