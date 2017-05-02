#!/bin/bash
# python ./manage.py run

if [ ! -d "flaskenv" ]; then
    echo "Python virtual environment for web app not present. Installing now..."
    virtualenv flaskenv
    source flaskenv/bin/activate
    pip install -r requirements.txt
    deactivate

fi

source flaskenv/bin/activate
python ./manage.py run

deactivate
