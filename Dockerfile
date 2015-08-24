# Pull base image.
FROM arteria/frozendata:latest

######################################
# Ensure we have python 2.7 installed
######################################
RUN yum -y update

RUN yum groupinstall -y development

RUN yum install -y zlib-dev openssl-devel sqlite-devel bzip2-devel wget tar

RUN cd /usr/src

RUN wget https://www.python.org/ftp/python/2.7.10/Python-2.7.10.tgz

RUN tar xzf Python-2.7.10.tgz

RUN cd Python-2.7.10 && ./configure && make altinstall

RUN wget --no-check-certificate https://pypi.python.org/packages/source/s/setuptools/setuptools-1.4.2.tar.gz

RUN tar -xvf setuptools-1.4.2.tar.gz

RUN cd setuptools-1.4.2 && python2.7 setup.py install

RUN curl https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py | python2.7 -

######################################
# Ensure we have pip installed
######################################

#RUN rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm

RUN yum -y install python-pip

######################################
# Install bcl2fastq 2.17
######################################
RUN yum install -y http://support.illumina.com/content/dam/illumina-support/documents/downloads/software/bcl2fastq/bcl2fastq2-v2.17.1.14-Linux-x86_64.rpm


######################################
# Setup for bcl2fastq-ws
######################################

RUN mkdir -p /var/log/bcl2fastq_logs/

# Expose default bcl2fastq-ws port
EXPOSE 8888
