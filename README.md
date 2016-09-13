Arteria bcl2fastq
=================

A self contained (Tornado) REST service for running Illuminas bcl2fastq.

Trying it out
-------------
The easiest way to try out `arteria-bcl2fastq` is to run it in the provided Vagrant box.

    # get the vagrant environment running
    # Please note that starting this vm requires 4 GB or RAM (since bcl2fastq requires alot of memory to run)
    vagrant up

    # ssh into it
    vagrant ssh

    # move into the vagrant working directory
    cd /vagrant

    # create a virtual environment and activate it
    virtualenv venv && source venv/bin/activate

    # update pip (unfortunately the installed verison is to old)
    pip install --upgrade pip    

    # install bcl2fastq (with -e for "editable" to make development easier)
    pip install -r requirements/dev .
    
Now you can try running it:

     bcl2fastq-ws --config config/ --port 8888

And then you can find a simple api documentation by opening up an additional terminal by running going to:

    curl http://localhost:8888/api | python -m json.tool

To try things out a bit more, you need to setup a path to watch and place some runfolders there, e.g.

    # Create the following folders under the /vagrant directory (or anywhere you like, but then
    # you need to make the corresponding changes in the `config/app.config`).
    mkdir ./bcl2fastq_logs ./runfolder_output

    # Clone a directory with test data
    git clone https://github.com/roryk/tiny-test-data.git

    # Start the service again
    bcl2fastq-ws --config config/ --port 8888

    # And now you can kick of running bcl2fastq on the small runfolder by:
    curl -X POST --data '{"additional_args": "--ignore-missing-bcls --ignore-missing-filter --ignore-missing-positions --ignore-missing-controls"}' http://localhost:8888/api/1.0/start/flowcell

    # You can poll its status on the returned link, or you can poll
    curl http://localhost:8888/api/1.0/status/ 

    
