#!/usr/bin/env python

""" This module mines relevant match IDs from the Steam API """
from __future__ import print_function
import json
import sys
import urllib
import os
import time

STEAM_BASE_URL = \
	"https://api.steampowered.com/IDOTA2Match_570/GetMatchHistoryBySequenceNum/v0001/?key="
SEQ_STRING = "&start_at_match_seq_num="
REQUESTS_STRING = "&matches_requested="
MIN_DURATION = 1200

# this should change every time a new patch is released
STARTING_MATCH_SEQ_NUM_FILE = "seq_num.txt"

NUM_GAME_LIMIT = 100000 * 100

def valid(match_json):
	""" checks if a game is valid: at least 20 mins long, all-pick ranked mode, no leavers

	match_json -- dictionary of a single match taken from the response json
	"""
	for player in match_json['players']:
		if player.get('leaver_status', 1) == 1:
			return False

	if match_json['duration'] < MIN_DURATION:
		return False

	if match_json['human_players'] != 10:
		return False

	if match_json['game_mode'] != 22:
		return False

	return True

class SteamMiner(object):
	""" Sends HTTP requests to Steam, parses the JSON that comes as a
	response and saves the relevant match IDs in a file

	Keyword arguments:
	number_of_games -- how many games should be processed
	out_file_handle -- handle of the file where the match IDs are written
	key -- Valve API key
	"""

	def __init__(self, number_of_games, out_file_handle, key):
		# Steam api max 100000 game per day
		self.games_number = min(number_of_games, NUM_GAME_LIMIT)
		self.out_file = out_file_handle
		self.api_key = key
		self.seq_num = self.get_starting_match_sequence_number()

	def get_starting_match_sequence_number(self):
		with open("seq_num.txt", "r") as f:
			num = int(f.readline())
			return num

	def save_sequence_number(self):
		with open("seq_num.txt", "w") as f:
			f.write(str(self.seq_num))

	def get_url(self, matches_requested):
		""" Concatenates the request into an URL

		matches_requested -- number of games requested (100 or lesser)
		"""
		return STEAM_BASE_URL + self.api_key + SEQ_STRING + str(self.seq_num) + \
				REQUESTS_STRING + str(matches_requested)

	def get_response(self, url_api, max_try=10):
		"""
		url_api -- the URL where the HTTP request is sent
		games_json -- JSON with valid response
		"""

		for i in xrange(max_try):
			response = urllib.urlopen(url_api)

			try:
				games_json = json.load(response)
			except ValueError:
				print("Cannot parse response.")
				time.sleep(60)
				continue

			if 'result' not in games_json:
				print("Invalid json string.")
				time.sleep(60)
				continue

			return games_json
		return None

	def run(self):
		""" Schedules the HTTP request, considering the fact that one request can handle
		up to 100 matches requested, so the process is done in chunks
		"""
		print("Start mining: %s" % self.seq_num)
		chunks = self.games_number / 100
		remainder = self.games_number - chunks * 100

		for i in range(chunks + 1):
			url = self.get_url(remainder if i == chunks else 100)

			response_json = self.get_response(url)

			if not response_json:
				break

			for match in response_json['result']['matches']:
				match_id = match['match_id']
				if valid(match):
					self.out_file.write(str(match_id) + "\n")
				self.seq_num = match['match_seq_num'] + 1

			print("Processed %d games" % ((i + 1) * 100))

		self.save_sequence_number()

def main():
	""" Main function """

	try:
		api_key = os.environ['STEAM_API_KEY']
	except KeyError:
		sys.exit("Please set API_KEY environment variable.")

	if len(sys.argv) < 3:
		sys.exit("Usage: %s <output_file> <number_of_games>" % sys.argv[0])

	try:
		out_file = open(sys.argv[1], "at")
	except IOError:
		sys.exit("Invalid output file")

	try:
		games_number = int(sys.argv[2])
	except ValueError:
		sys.exit("Invalid number of games")

	miner = SteamMiner(games_number, out_file, api_key)
	miner.run()

	out_file.close()


if __name__ == "__main__":
	main()
