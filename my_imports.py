from variables import *
from csv_functions import *
from functions import *
from mp3 import *
from log import *
from spotify import *
from mp3 import *

import os
import re
import csv
import datetime

import telebot
from telebot import types

import threading # to use lock
import time # for sleep
import subprocess # to be able to run another python script inside current one
import fcntl # to lock writing simultaneously on one file
import portalocker # for experimental queue handler bypass - used in db_csv_append
import random # to choose random spotify app to be used in api