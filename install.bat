@echo off 

if not exist "venv\" python -m venv venv
call venv\Scripts\activate.bat

pip install -r requirements.txt
pip install -e .

call venv\Scripts\deactivate.bat
