# Care Platform

Care Platform is a back-end project for managing corona related process in hospitals

## Installation
1. Clone the repo
   1. Using ssh key
      ```
      git clone git@github.com:joshtechnologygroup/care-platform.git
      ```
   2. Using https
      ```
      git clone https://github.com/joshtechnologygroup/care-platform.git
      ```
2. Install Postgres DB
   ```
   sudo apt-get install postgresql postgresql-contrib libpq-dev
   ```
3. Install dependencies
   ```
   pip install -r reqs/local.txt
   ```
4. Create local settings file by coping **local.py.template** into **local.py**
   ```
   cp care/settings/local.py.template care/settings/local.py 
   ```
5. Create Database and update DB credential in **local.py**
6. Run migration
   ```
   python manage.py migrate
   ```
7. Load Initial data
    ```
    python manage.py setupdata
    ```
8. Load Test data
    ```
    python manage.py setuptestdata
    ```
9. Start server
   ```
   python manage.py runserver
   ```
Check out running server at [localhost](http://127.0.0.1:8000)

## License
[MIT](https://choosealicense.com/licenses/mit/)