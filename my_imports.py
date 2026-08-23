# my defined files
from variables import *
from db_functions import *
from functions import *
from mp3 import *
from log import *
from spotify import *
from mp3 import *
from redis_fast_cache import get_telegram_audio_id_cached

# general imports
import os
import re
import datetime
import traceback
import asyncio

# telebot
import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Update # for new webhook system
from telebot.types import InlineQueryResultCachedAudio, ReactionTypeEmoji, ReplyParameters

import threading # to use lock
import time # for sleep
import subprocess # to be able to run another python script inside current one
import fcntl # to lock writing simultaneously on one file
import portalocker # for experimental queue handler bypass - used in db_csv_append
import random # to choose random spotify app to be used in api

import sqlite3 # to use sqlite3 database
import boto3 # for S3 upload

from fastapi import FastAPI, Request, Response