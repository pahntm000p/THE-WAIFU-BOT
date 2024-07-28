@echo off
TITLE Github Quick-Pull

:: Print the branch cause ..oooooo fancy!
echo Pulling from branch: 
git branch
echo.
:: Use token in the repository URL
git pull https://yourusername:yourtoken@github.com/yourusername/yourrepo.git
