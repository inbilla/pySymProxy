@echo off
set CURPATH=%~dp0
echo %CURPATH%
pushd %CURPATH%

pip install -r requirements.txt

python server.py

popd