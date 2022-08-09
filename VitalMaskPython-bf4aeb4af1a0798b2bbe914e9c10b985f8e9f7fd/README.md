# VitalMask Desktop Developer Environment
## Welcome to v2 of the VitalMask desktop application. Now in Python!
<br/><br/>

# Setting Up for Development
If you are looking at this repository, chances are you want to clone a local development copy of the Vital Mask Desktop application that you can run, test, and develop. If you only want a runnable version, see the [Google Drive](https://drive.google.com/drive/folders/1f1zzHtFY2vvJhoHhC9VCl_fCAuDE6C9g?usp=sharing) for standalone executables and setup clients.

## 1. Installing and Setting Up Python
To get this working, first you will need to install [Python](https://www.python.org/downloads/).
You will also need a Python IDE. I Recommend using [Visual Studio Code](https://code.visualstudio.com/) with the Python extension.

You may then clone this repo.

## 2. Creating and Running a Virtual Environment
Setting up a virtual environment is crucial for this project if you wish to package runnable installations out of the application. It ensures that you have a separate Python environment tailored for developing this application, with only the packages and dependencies that this application uses.

First, navigate to the cloned repo in terminal or command prompt and create a virtual environment (it will be automatically gitignored as long as you name it kivy_venv):
```bash
python -m virtualenv kivy_venv
```
Then, run the virtual environment (this step needed *EVERY* time you open the terminal):
```bash
kivy_venv\Scripts\activate
```
Lastly, install all dependencies into the venv as outlined in the above section.

<br/><br/>

## 3. Installing Dependencies
This application relies on a few packages and libraries to work.

To make sure you have the latest pip tools: 
```bash
python -m pip install --upgrade pip wheel setuptools virtualenv
```
To install Kivy along with examples:
```bash
python -m pip install kivy[base] kivy_examples
```
To install BLEAK:
```bash
pip install bleak
```
To install PyInstaller VERSION 4.3 IS A MUST:
```bash
pip install pyinstaller==4.3
```
To install Psycopg2:
```bash
pip install psycopg2
```
To install numpy:
```bash
pip install numpy
```
^This list will be updated according to our needs.

<br/><br/>

# Rolling Out a Release Version
To make a copy of this application usable for customers, you need to (1) create a runnable installation with PyInstaller, (2) sign the installation with SignTools, and (3) package that installation into an installation client with InnoSetup.

A Windows computer will need to be used.

Information is described in the three below steps:

<br/><br/>

## 1. Creating Runnable Installation
First, if either "build" or "dist" folders exist in the repo, delete them.
If they do not exist, you may not have setup PyInstaller. Make sure it's installed, then run:
```bash
python -m PyInstaller --name VitalMaskPython --icon applogo.ico dashboard.py
```

Then, run the virtual environment as described in a previous corresponding section.

A VitalMaskPython.spec should have been created in the installation directory. Open it and please paste in a spec from the [Spec Document](https://docs.google.com/document/d/1KF0NZNz4PSf2cdX3VCm1mYgGBWBEY1z3Jrr5-NqoL5A/edit?usp=sharing) we have created. Feel free to tweak it and paste a new spec onto the document.
Remember to change the paths in the spec as stressed in the doc!!!

Finally, use
```bash
python -m PyInstaller VitalMaskPython.spec
```
This should create a VitalMaskPython folder in VitalMaskPython/dist, which contains the entirety of the runnable installation. No matter where this folder is, clicking the contained .exe should run the application with no problem!

<br/><br/>

## 2. Signing Software (Windows only)
We'll need to sign our .exe files after creating a runnable installation so that we show the software is valid and legal.

For now, we'll use our personal signatures because I guess it's better than nothing.

First, make sure [SignTools](https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk/) is installed.

Add signtool.exe to path if needed (It's in Program Files(x86)\Windows Kits\10\bin\[sdk_version]\x64\signtools.exe).

Open command prompt, navigate to location of newly created .exe, and type:
```bash
signtool sign /a [executable file]
```
This should sign the executable with your "best" certificate you have access to. Error if you don't have any.

<br/><br/>

## 3. Creating a Setup Client (Windows only)
For this, we use [InnoSetup](https://jrsoftware.org/isdl.php) along with separate Encryption module you can find on the same page!

Install InnoSetup and take the Runnable Installation you created and then signed.

<br/><br/>

## Troubleshooting
**Necessary for packaging app!**
**If you receive an error "Window Not Found", navigate to your Python file and open these two files:**
```bash
Python\Python37-32\lib\site-packages\kivy\core\__init__.py
Python\Python37-32\lib\site-packages\kivy\factory.py
```
and add this import:
```bash
from importlib import __import__
```

**If you have having permission issues trying to run the virtual environment:**
```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then run.
<br/>

## Contributors 
- Ray Wei (rayw2007)
- Daniel Stabile (falsefeint)
- Rishi Singhal (rs872)




